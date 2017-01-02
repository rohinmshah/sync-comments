import json, os.path, pickle, sys, time
from api import fbApi, disqusApi, eaforumApi
from adts import Post, RealComment
from config import *

# post: A Post object that has an id for the given website
# website: Which website to copy comments from.
# Copies any new comments from website to Disqus.
# Note website is not a URL, it is simply an identifier like "Facebook" that is
# used to extract information out of the Post object.
def sync_website_comments(post, website, api):
    if website not in post.other_ids:
        return

    copied_comments = post.copied_comments[website]
    thread_id = post.other_ids[website]
    
    def loop(comment_node, disqus_parent):
        # Handle the current comment
        comment = comment_node.item
        if comment.id not in copied_comments:
            disqus_id = disqusApi.guarded_make_comment(comment, thread_id, disqus_parent)
            copied_comments[comment.id] = disqus_id

        # Recurse over the children
        for child in comment_node.children:
            loop(child, copied_comments[comment.id])
            
    root = api.get_comments(thread_id)
    for node in root.children:
        loop(node, None)

# TODO: Currently we depend on the pickled file remaining -- if the pickled file
# is deleted, then all the comments will be re-copied, causing duplicates.
def create_all_posts_data_structure():
    previous_all_posts = []
    if os.path.isfile(PICKLED_POSTS_FILE):
        with open(PICKLED_POSTS_FILE) as f:
            previous_all_posts = pickle.load(f)

    post_data = None
    with open(USER_POSTS_FILE) as f:
        post_data = json.load(f)

    all_posts = []
    for post_dict in post_data:
        found = False
        for old_post in previous_all_posts:
            if old_post.disqus_id == post_dict['disqus']:
                all_posts.append(old_post)
                found = True
                break

        if not found:
            new_post = Post(post_dict['disqus'], post_dict['others'])
            all_posts.append(new_post)

    return all_posts

def loop():
    all_posts = create_all_posts_data_structure()
    counter = 0
    while True:
        counter += 1
        print 'Iteration', counter
        for post in all_posts:
            sync_website_comments(post, EA_FORUM_STRING, eaforumApi)
            sync_website_comments(post, FACEBOOK_STRING, fbApi)

        with open(PICKLED_POSTS_FILE, 'w') as f:
            pickle.dump(all_posts, f)

        time.sleep(DELAY)

def usage(name):
    print 'python [-i]', name, '*function*'
    print 'Using the -i flag will put you in interactive mode, with results from the query in the "result" variable'
    print 'disqus-ids: Get the recent post ids and titles from Disqus'
    print 'go: Run the main loop that syncs comments every 5 minutes'
    print 'refresh-fb: Get a new Facebook access code'
    print 'refresh-disqus: Get a new Disqus access code'

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
    if len(sys.argv) == 2:
        if sys.argv[1] == 'refresh-fb':
            result = fbApi.get_access_token()
            print result
            print 'Put this in FB_LONG_CODE in keys.py and restart'
        elif sys.argv[1] == 'refresh-disqus':
            result = disqusApi.get_access_token()
            print result
            print 'Put this in DISQUS_ADMIN_ACCESS_TOKEN in keys.py and restart'
        elif sys.argv[1] == 'go':
            loop()
        elif sys.argv[1] == 'disqus-ids':
            result = disqusApi.get_post_ids_and_titles()
            print result
        elif sys.argv[1] == 'fb-posts':
            result = fbApi.get_posts()
            for post in result:
                print post
        elif sys.argv[1] == 'test':
            result = test()
            print result
        else:
            usage(sys.argv[0])
    else:
        usage(sys.argv[0])
