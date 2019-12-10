import base36
# Import before importing the bot
# Sets up test environment
import tests.test_utils as tutils
from modbot.utils import utcnow

class FakeSubreddit():
    class FakeWiki():
        def __init__(self, name, subreddit):
            self.name = name
            self.content = ""
            self.subreddit = subreddit

        @property
        def content_md(self):
            return self.content

        def set_content(self, content):
            self.content = content

    def __init__(self, name):
        self.name = name
        self.wikis = {}
        self.submissions = []
        self.subreddit_type = ["public"]

    @property
    def display_name(self):
        return self.name

    def get_wiki(self, name):
        if name not in self.wikis:
            self.wikis[name] = self.FakeWiki(name, self)

        return self.wikis[name]

    def edit_wiki(self, name, content):
        if name not in self.wikis:
            self.wikis[name] = self.FakeWiki(name, self)

        self.wikis[name].set_content(content)

    def add_submission(self, submission):
        self.submissions.append(submission)

class FakeSubmission():
    crt_id = 0
    def __init__(self, subreddit_name, author_name, title):
        self.id = base36.dumps(FakeSubmission.crt_id)
        self.shortlink = "https://redd.it/" + self.id
        self.created_utc = utcnow()

        self.author = get_user(author_name)
        self.title = title

        self.is_crosspostable = True
        self.link_flair_text = None

        # Add submission to subreddit
        self.subreddit = get_subreddit(subreddit_name)
        self.subreddit.add_submission(self)

        # Add to global cache and increment submission id
        cache_submissions[self.id] = self
        FakeSubmission.crt_id += 1

class FakeUser():
    def __init__(self, name):
        self.name = name
        self.inbox = []

    def message(self, subject, text):
        self.inbox.append((subject, text))

class FakeModerator():
    def moderator_subreddits(self):
        sub_lst = []

        for i in moderated_subs:
            sub_lst.append(FakeSubreddit(i))
        return sub_lst

class FakePRAW():
    def __init__(self, name):
        print("Create fake PRAW " + name)
        self.user = FakeModerator()

    def subreddit(self, name):
        print("Get sub " + name)

        return get_subreddit(name)

    def submission(self, url):
        id = url.split("/")[-1]

        return cache_submissions[id]

# Cache of various objects
cache_reddit = {}
cache_subreddit = {}
cache_submissions = {}
cache_users = {}

set_initial_submission = None
set_initial_comment = None
new_all_sub = None
new_all_comm = None
time_trigger = None
moderated_subs = None

def set_praw_opts(credentials, user_agent):
    """
    Set authentication options
    """
    pass

def get_reddit(name="default", force_create=False):
    """
    Get fake PRAW instance
    """

    if name not in cache_reddit:
        cache_reddit[name] = FakePRAW(name)

    return cache_reddit[name]

def get_subreddit(name):
    """
    Get fake subreddit instance
    """

    if name not in cache_subreddit:
        cache_subreddit[name] = FakeSubreddit(name)

    return cache_subreddit[name]

def get_user(name):
    """
    Get fake subreddit instance
    """

    if name not in cache_users:
        cache_users[name] = FakeUser(name)

    return cache_users[name]

def get_wiki(subreddit, name):
    return subreddit.get_wiki(name)

def edit_wiki(subreddit, wiki_name, content):
    subreddit.edit_wiki(wiki_name, content)

def thread_sub(set_initial_sub, new_sub):
    global set_initial_submission
    global new_all_sub

    set_initial_submission = set_initial_sub
    new_all_sub = new_sub

def thread_comm(set_initial_comm, new_comm):
    global set_initial_comment
    global new_all_comm

    set_initial_comment = set_initial_comm
    new_all_comm = new_comm

def set_initial_sub(sub):
    set_initial_submission(sub)

def tick(period, trigger):
    global time_trigger
    time_trigger = trigger

def do_tick():
    time_trigger(utcnow())

def advance_time_30s():
    for _ in range(30):
        do_tick()
        tutils.advance_time(1)

def advance_time_60s():
    for _ in range(60):
        do_tick()
        tutils.advance_time(1)

def set_moderated_subs(lst):
    global moderated_subs
    moderated_subs = lst