class Tree:
    def __init__(self, item, parent=None):
        self.item = item
        self.parent = parent
        self.children = []

    def add_child(self, item):
        child = Tree(item, self)
        self.children.append(child)
        return child

    def __str__(self):
        return self.str_help()

    def str_help(self, indent=''):
        if not self.children:
            return indent + str(self.item)
        recurse = [c.str_help(indent + '  ') for c in self.children]
        return indent + str(self.item) + '\n' + '\n'.join(recurse)

class Comment:
    def __init__(self):
        pass

class RealComment(Comment):
    # website, post and id together should uniquely identify a comment
    def __init__(self, website, post, id, url, username, is_owner, content):
        Comment.__init__(self)
        self.website = website
        self.post = post
        self.id = id
        self.url = url
        self.username = username
        self.is_owner_comment = is_owner
        self.content = content

    def __str__(self):
        message = self.content
        if len(self.content) > 100:
            message = message[:100] + '...'
        return str(self.username) + ': ' + str(message)

class FakeComment(Comment):
    # For things like pointers to comments, or things where the
    # comment score is below a threshold and so the comment text isn't
    # visible, etc.
    def __init__(self, stuff):
        Comment.__init__(self)
        self.stuff = stuff

class Post:
    def __init__(self, disqus_id, other_ids):
        self.disqus_id = disqus_id
        self.other_ids = other_ids
        self.copied_comments = { k:{} for k in other_ids }

    def __str__(self):
        return 'Post #' + str(self.disqus_id) + ' with comments ' + str(self.copied_comments)
        
