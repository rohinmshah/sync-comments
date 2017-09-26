import requests
import re
from config import *
from keys import *
from adts import *
from urlparse import parse_qs
from html import HTML

import urllib2
from bs4 import BeautifulSoup

Request = requests.Request

class API:
    def __init__(self, debug):
        self.debug = debug

class DisqusAPI(API):
    def __init__(self,
                 debug,
                 global_key=DISQUS_GLOBAL_KEY,
                 app_key=DISQUS_PUBLIC_KEY,
                 app_secret=DISQUS_SECRET,
                 forum_name=DISQUS_FORUM_NAME,
                 owner_access_token=DISQUS_OWNER_ACCESS_TOKEN,
                 admin_access_token=DISQUS_ADMIN_ACCESS_TOKEN,
                 limit=100):
        API.__init__(self, debug)
        self.global_key = global_key
        self.app_key = app_key
        self.app_secret = app_secret
        self.forum_name = forum_name
        self.owner_access_token = owner_access_token
        self.admin_access_token = admin_access_token
        self.limit = limit

    # Implements the options taken by get and post by mutating the arguments
    # dictionary.
    # Return value unspecified.
    def fix_arguments(self, arguments, options):
        key = self.global_key if 'useGlobal' in options else self.app_key
        arguments['api_key'] = key

        if 'noForum' not in options:
            arguments['forum'] = self.forum_name
        if 'access_token' in options:
            arguments['access_token'] = self.admin_access_token
        if 'noLimit' not in options and 'limit' not in arguments:
            arguments['limit'] = self.limit

    # Makes a request to the Disqus API with the given parameters.
    # request_type: Either 'get' or 'post', whether to use GET or POST.
    # endPoint: A string identifier for the Disqus API function to invoke.
    # arguments: Query parameters for the endpoint.
    # options: Various options that customize how the request is made.
    # Returns: The result of the request (an HTTPResponse object).
    def request(self, request_type, endPoint, arguments={}, options=[]):
        assert request_type in ['get', 'post']

        # Make a copy of arguments, since we mutate it
        arguments = { k:arguments[k] for k in arguments }
        self.fix_arguments(arguments, options)

        url = 'https://disqus.com/api/3.0/' + endPoint
        fn = requests.get if request_type == 'get' else requests.post
        result = fn(url, arguments)
        if result.status_code != 200:
            print result.text
        return result

    # Makes a GET request to the Disqus API with the given parameters.
    def get(self, endPoint, arguments={}, options=[]):
        return self.request('get', endpoint, arguments, options)

    # Makes a POST request to the Disqus API with the given parameters.
    def post(self, endPoint, arguments={}, options=[]):
        if self.debug:
            print 'Squelching POST request in debug mode to Disqus endpoint', endPoint
            return
        # We always allow a POST request to not specify a limit.
        if 'limit' not in arguments and 'noLimit' not in options:
            options.append('noLimit')
        return self.request('post', endpoint, arguments, options)

    # thread: Id of the post to get comments for (as a string).
    # Returns: The result of the request (an HTTPResponse object).
    # Calling JSON on the response will have the required data.
    def get_comments_on_thread(self, thread):
        return self.get('threads/listPosts.json', {'thread': thread})

    # Returns: The result of the request (an HTTPResponse object).
    # Calling JSON on the response will have the required data.
    def get_posts(self):
        return self.get('forums/listThreads.json')

    def get_post_ids_and_titles(self):
        result = self.get_posts().json()['response']
        return [(post['id'], post['clean_title']) for post in result]

    # Converts a RealComment into HTML suitable for posting to Disqus.
    # comment: The RealComment object to construct a message from.
    # Returns: Stringified HTML for the comment text.
    def create_message(self, comment):
        atag = HTML().a(comment.website, href=comment.url)
        source = HTML().p('Synced from ' + str(atag), escape=False)
        return str(source) + comment.content

    def guarded_make_comment(self, comment, thread, parent=None):
        if '[nocopy]' in comment.content:
            comment.content = '<p><i>Comment hidden by request</i></p>'
        return self.make_comment(comment, thread, parent)

    # Adds and approves a comment as a reply to the entity identified by thread.
    # The comment will immediately appear on the website.
    # If debug is true, then the comment is not added to the website and instead
    # a message is printed saying that the comment would have been added.
    # comment: The comment to post, as a RealComment object.
    # thread: The id of the parent comment that this is a reply to, or the id of
    # the blog post if it is a top-level comment. This is a string.
    # Returns: The Disqus ID of the created comment.
    def make_comment(self, comment, thread, parent=None):
        message = self.create_message(comment)
        if comment.is_owner_comment:
            print 'Adding owner comment from', comment.website
            if self.debug:
                print 'Not adding owner comment since we are in debug mode'
                return 0
            req = self.add_owner_comment(message, thread, parent)
            return req.json()['response']['id']
        else:
            name = comment.username.strip().split()[0]
            print 'Add comment by', name, 'from', comment.website
            if self.debug:
                print 'Not adding comment since we are in debug mode'
                return 0
            req = self.add_comment(name, message, thread, parent)
            comment_id = req.json()['response']['id']
            self.approve_comment(comment_id)
            return comment_id

    # Adds a comment as a reply to the entity identified by thread.
    # By default, this is a guest comment and so is subject to moderation.
    # name: The author of the comment, as a plain text string.
    # comment: The comment to post, as stringified HTML.
    # thread: The id of the parent comment that this is a reply to, or the id of
    # the blog post if it is a top-level comment. This is a string.
    # Returns: The result of the request (an HTTPResponse object).
    def add_comment(self, name, comment, thread, parent=None):
        args = {
            'message': comment,
            'thread': thread,
            'author_name': name,
            'author_email': 'example@disqus.com'
        }
        if parent:
            args['parent'] = parent
        # See https://disqus.com/home/channel/discussdisqus/discussion/channel-discussdisqus/disqus_api_create_post_as_guest/
        # for an explanation of why we use the global key
        return self.post('posts/create.json', args, ['useGlobal', 'noForum'])

    def add_owner_comment(self, comment, thread, parent=None):
        args = {
            'message': comment,
            'thread': thread
        }
        if parent:
            args['parent'] = parent
        return self.post('posts/create.json', args, ['access_token', 'noForum'])

    # comment_id: The id of the comment to approve, as a string.
    # Returns: The result of the request (an HTTPResponse object).
    def approve_comment(self, comment_id):
        return self.post('posts/approve.json',
                         { 'post': comment_id },
                         ['access_token', 'noForum'])

    # Returns: An access token for Disqus, as a string.
    # Involves some user interaction.
    def get_access_token(self):
        redirect = 'http://rohinshah.com/'
        oreq = Request('GET', "https://disqus.com/api/oauth/2.0/authorize",
                       params = {
                           'client_id': self.app_key,
                           'scope': 'read,write,admin',
                           'response_type': 'code',
                           'redirect_uri': redirect
                       })
        url = oreq.prepare().url
        print 'Load this in your browser:', url
        print 'Paste the url it redirects you to:'
        result = raw_input("> ")
        code = re.findall('code=(.*)$', result)[0]

        r = requests.post('https://disqus.com/api/oauth/2.0/access_token/',
                          {
                              'grant_type': 'authorization_code',
                              'client_id': self.app_key,
                              'client_secret': self.app_secret,
                              'redirect_uri': redirect,
                              'code': code
                          })

        return r.json()['access_token']


class FacebookAPI(API):
    def __init__(self,
                 debug,
                 app_id=FB_APP_ID,
                 app_secret=FB_APP_SECRET,
                 user_id=FB_OWNER_ID,
                 access_token=FB_LONG_CODE):
        API.__init__(self, debug)
        self.app_id = app_id
        self.app_secret = app_secret
        self.user_id = user_id
        self.access_token = access_token

    def request(self, request_type, endpoint, arguments, options):
        assert request_type in ['get', 'post']
        fn = requests.get if request_type == 'get' else requests.post
        url = 'https://graph.facebook.com/v2.8/' + endpoint
        arguments = { k:arguments[k] for k in arguments }
        if 'no_access_token' not in options:
            arguments['access_token'] = self.access_token
        return fn(url, arguments)

    def get(self, endpoint, arguments={}, options=[]):
        return self.request('get', endpoint, arguments, options)

    def post(self, endpoint, arguments={}, options=[]):
        return self.request('post', endpoint, arguments, options)

    def get_posts(self):
        return self.get('me/posts').json()['data']

    def make_comment_object(self, post_id, data):
        url = 'https://www.facebook.com/' + data['id']
        is_owner = data['from']['id'] == self.user_id
        return RealComment(FACEBOOK_STRING, post_id, data['id'], url, data['from']['name'], is_owner, data['message'])

    # object_id: The id of a Facebook node that has the comments edge
    # Returns: A list of Facebook comments (as dictionaries)
    def get_one_level_comments(self, object_id):
        result = self.get(object_id + '/comments').json()
        return result['data']

    def get_comments(self, post_id):
        top_level = self.get_one_level_comments(post_id)
        root = Tree(None)
        for comment_dict in top_level:
            comment_obj = self.make_comment_object(post_id, comment_dict)
            comment_tree_node = root.add_child(comment_obj)
            for reply_dict in self.get_one_level_comments(comment_dict['id']):
                reply_obj = self.make_comment_object(post_id, reply_dict)
                comment_tree_node.add_child(reply_obj)
        return root

    # Returns: A long-term access token for Facebook as a string.
    # Involves some user interaction.
    def get_access_token(self):
        redirect = 'http://rohinshah.com/'
        oreq = Request('GET', "https://www.facebook.com/dialog/oauth",
                       params = {
                           'client_id': self.app_id,
                           'scope': 'public_profile,user_posts,user_friends',
                           'redirect_uri': redirect
                       })
        url = oreq.prepare().url
        print 'Load this in your browser:', url
        print 'Paste the url it redirects you to:'
        result = raw_input("> ")
        code = re.findall('code=([^#]*)#_=_$', result)[0]

        def get_code(response):
            return response.json()['access_token']
    
        short_code = get_code(
            requests.get('https://graph.facebook.com/oauth/access_token',
                         {
                             'client_id': self.app_id,
                             'redirect_uri': redirect,
                             'client_secret': self.app_secret,
                             'code': code
                         }))

        return get_code(
            requests.get('https://graph.facebook.com/oauth/access_token',
                         {
                             'client_id': self.app_id,
                             'client_secret': self.app_secret,
                             'grant_type': 'fb_exchange_token',
                             'fb_exchange_token': short_code
                         }))

class EAForumAPI(API):
    DIV_START = '<div class="md">'
    DIV_END = '</div>'
    def __init__(self, debug):
        API.__init__(self, debug)

    # url: The url of the EA Forum post that the comment comes from
    # commentDiv: The BeautifulSoup div representing the comment
    #             (This is the one with class "entry".)
    # Returns: A Comment object. Tries to make a RealComment object by scraping
    #          relevant information, if this is not possible it returns a
    #          FakeComment that keeps the information to be used later.
    def make_comment_object(self, url, commentDiv):
        try:
            id = unicode(commentDiv.findPrevious(class_='parent').a['name'])
            separator = '#' if url[-1] == '/' else '/#'
            comment_url = url + separator + id
            author = unicode(commentDiv.find(class_='comment-author').a.text)
            is_owner = (author == 'rohinmshah')
            contentDiv = commentDiv.find(class_='comment-content')
            msg = unicode(contentDiv.find(class_='md')).strip()
            if msg.startswith(self.DIV_START) and msg.endswith(self.DIV_END):
                msg = msg[len(self.DIV_START):-len(self.DIV_END)].strip()
            msg = msg.replace('<ul>', '<p>').replace('</ul>', '</p>')
            msg = msg.replace('<li>', '* ').replace('</li>', '')
            return RealComment(EA_FORUM_STRING, url, id, comment_url, author, is_owner, msg)
        except (KeyError, AttributeError, TypeError) as e:
            return FakeComment((url, commentDiv))

    # url: A url pointing to an EA Forum post.
    # Returns a Tree containing RealComments scraped from the post.
    def get_comments(self, url):
        page = urllib2.urlopen(url)
        soup = BeautifulSoup(page, "lxml")
        comments = soup.find(id='comments').find_all(class_='entry')
        root = Tree(None)
        id_to_node = {}
        unhandled = []
        for commentDiv in comments:
            comment = self.make_comment_object(url, commentDiv)
            if not isinstance(comment, RealComment):
                unhandled.append(comment)
                continue

            parent_node = root
            parentDiv = commentDiv.find(class_='parent')
            if parentDiv:
                parent_id = parentDiv.a['href'][1:]
                parent_node = id_to_node[parent_id]

            new_node = parent_node.add_child(comment)
            id_to_node[comment.id] = new_node

        # TODO: Do something with unhandled
        return root
