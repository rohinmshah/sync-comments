import argparse, json, os.path, pickle, sys, time
from api import FacebookAPI, DisqusAPI, EAForumAPI
from adts import Post, RealComment
from config import *

# post: A Post object that has an id for the given website
# website: Which website to copy comments from.
# Copies any new comments from website to Disqus.
# Note website is not a URL, it is simply an identifier like "Facebook" that is
# used to extract information out of the Post object.
def sync_website_comments(post, website, api, save_fn, params):
    if website not in post.other_ids:
        return

    copied_comments = post.copied_comments[website]
    disqusApi = DisqusAPI(params.debug)
    
    def loop(comment_node, disqus_parent):
        # Handle the current comment
        comment = comment_node.item
        if comment.id not in copied_comments:
            disqus_id = disqusApi.guarded_make_comment(comment, post.disqus_id, disqus_parent, params.debug)
            copied_comments[comment.id] = disqus_id
            save_fn()
            time.sleep(10)

        # Recurse over the children
        for child in comment_node.children:
            loop(child, copied_comments[comment.id])
    
    thread_ids = post.other_ids[website]
    if type(thread_ids) != type([]):
        thread_ids = [ thread_ids ]
    for thread_id in thread_ids:
        root = api.get_comments(thread_id)
        for node in root.children:
            loop(node, None)

# TODO: Currently we depend on the pickled file remaining -- if the pickled file
# is deleted, then all the comments will be re-copied, causing duplicates.
def create_all_posts_data_structure(params):
    previous_all_posts = []
    if os.path.isfile(PICKLED_POSTS_FILE):
        with open(PICKLED_POSTS_FILE) as f:
            previous_all_posts = pickle.load(f)

    post_data = None
    with open(USER_POSTS_FILE) as f:
        post_data = json.load(f)

    def find_old_post(id):
        matching_posts = [p for p in previous_all_posts if p.disqus_id == id]
        return matching_posts[0] if matching_posts else None

    def get_post_object(post_dict):
        old_post_object = find_old_post(post_dict['disqus'])
        new_post_object = Post(post_dict['disqus'], post_dict['others'])
        if old_post_object is not None and not old_post_object.has_same_links(new_post_object):
            if params.prefer_user_post_data:
                # In this scenario, we still want to keep the record
                # of copied comments in the old post object -- we only
                # want to update the link information.
                old_post_object.other_ids = new_post_object.other_ids
            else:
                raise ValueError('Old post and new post have different links!\nOld post: %s\nNew post: %s' % (old_post_object.other_ids, new_post_object.other_ids))
        return old_post_object if old_post_object else new_post_object

    all_posts = [get_post_object(post_dict) for post_dict in post_data]
    # get_post_object may have changed data, so save that data
    save(all_posts, params)
    return all_posts


def save(all_posts, params):
    if params.debug:
        print 'Not pickling all_posts since we are in debug mode'
    else:
        with open(PICKLED_POSTS_FILE, 'w') as f:
            pickle.dump(all_posts, f)

def sync(all_posts, params):
    save_fn = lambda: save(all_posts, params)
    eaForumApi = EAForumAPI(params.debug)
    facebookApi = FacebookAPI(params.debug)
    for post in all_posts:
        sync_website_comments(post, EA_FORUM_STRING, eaForumApi, save_fn, params)
        sync_website_comments(post, FACEBOOK_STRING, facebookApi, save_fn, params)

def loop(params):
    all_posts = create_all_posts_data_structure(params)
    counter = 0
    while True:
        counter += 1
        print 'Iteration', counter
        sync(all_posts, params)

        time.sleep(DELAY)

def usage_str():
    result = 'Supported commands:\n'
    result += 'disqus-ids: Get the recent post ids and titles from Disqus\n'
    result += 'go: Run the main loop that syncs comments every 5 minutes\n'
    result += 'refresh-fb: Get a new Facebook access code\n'
    result += 'refresh-disqus: Get a new Disqus access code\n'
    return result

def test():
    # comment = RealComment(EA_FORUM_STRING, "http://effective-altruism.com/ea/154/thoughts_on_the_meta_trap/", '9gu', "http://effective-altruism.com/ea/154/thoughts_on_the_meta_trap/#9gu", 'rohinmshah', True, 'Test comment by owner')
    # cid = disqusApi.guarded_make_comment(comment, '5397217386')
    # print cid
    
    # comment = RealComment(EA_FORUM_STRING, "http://effective-altruism.com/ea/154/thoughts_on_the_meta_trap/", '9gu', "http://effective-altruism.com/ea/154/thoughts_on_the_meta_trap/#9gu", 'auser', False, 'Test reply by guest')
    # r = disqusApi.guarded_make_comment(comment, '5397217386', cid)
    # print r
    # r = disqusApi.get_comments_on_thread('5397217386')
    # r = disqusApi.get_post_ids_and_titles()
    # return r
    return None

result = 0
if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Copy comments from posts to blog.', epilog=usage_str())
    parser.add_argument('command', nargs=1)
    parser.add_argument('--debug', action='store_const',
                        const=True, default=False,
                        help='Run in debug mode, printing all actions that would be taken, but not actually performing them')
    parser.add_argument('--prefer_user_post_data', action='store_const',
                        const=True, default=False,
                        help='When the pickle file and the user post data conflict, use the results from the user post data rather than raising an error.')
    params = parser.parse_args()
    command = params.command[0]

    if command == 'refresh-fb':
        result = FacebookAPI(params.debug).get_access_token()
        print result
        print 'Put this in FB_LONG_CODE in keys.py and restart'
    elif command == 'refresh-disqus':
        result = DisqusAPI(params.debug).get_access_token()
        print result
        print 'Put this in DISQUS_ADMIN_ACCESS_TOKEN in keys.py and restart'
    elif command == 'go':
        loop(params)
    elif command == 'sync':
        sync(create_all_posts_data_structure(params), params)
    elif command == 'disqus-ids':
        result = DisqusAPI(params.debug).get_post_ids_and_titles()
        print result
    elif command == 'fb-posts':
        result = FacebookAPI(params.debug).get_posts()
        for post in result:
            print post
    elif command == 'test':
        result = test()
        print result
    else:
        print usage_str()
