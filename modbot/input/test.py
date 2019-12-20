import base36
import datetime
###############################################################################
# Override default thread implementation
###############################################################################
import modbot.utils as utils
class TestThread():
    def __init__(self, target=None, name=None, args=()):
        self.name = name
        self.target = target
        self.args = args

    def setDaemon(self, state):
        pass

    def start(self):
        self.target(*self.args)

    def isAlive(self):
        return False

# Hook up fake thread
utils.BotThread = TestThread
###############################################################################

###############################################################################
# Override time source
###############################################################################
GLOBAL_TIME = 0
def set_time(val):
    global GLOBAL_TIME
    GLOBAL_TIME = val

def advance_time(val):
    global GLOBAL_TIME
    set_time(GLOBAL_TIME + val)

def get_time():
    return datetime.datetime.fromtimestamp(GLOBAL_TIME)

utils.get_utcnow = get_time
###############################################################################

###############################################################################
# Override URL fetcher
###############################################################################
import modbot.utils_title as utils_title
class FakeParser():
    def __init__(self, url):
        self.title = cache_urls[url]

utils_title.Parser = FakeParser
###############################################################################

from modbot.bot import bot
from modbot.storage import set_storage_loc, clean_storage_loc

# Cache of various objects
cache_reddit = {}
cache_subreddit = {}
cache_submissions = {}
cache_users = {}
cache_urls = {}

set_initial_submission = None
set_initial_comment = None
new_all_sub = None
new_all_comm = None
time_trigger = None
moderated_subs = None

class FakeSubreddit():

    class FakeWiki():
        def __init__(self, name, subreddit):
            self.name = name
            self.content = ""
            self.subreddit = subreddit
            self.revision_by = get_user("BigDaddy")
            self.revision_date = 0

        @property
        def content_md(self):
            return self.content

        def set_content(self, content, author):
            self.content = content
            self.revision_by = get_user(author)
            self.revision_date = int(utils.utcnow())

    def __init__(self, name):
        self.name = name
        self.wikis = {}
        self.submissions = []
        self.subreddit_type = ["public"]
        self.sub_flairs = None

    @property
    def display_name(self):
        return self.name

    def get_wiki(self, name):
        if name not in self.wikis:
            self.wikis[name] = self.FakeWiki(name, self)

        return self.wikis[name]

    def edit_wiki(self, name, content, author="BigDaddy"):
        if name not in self.wikis:
            self.wikis[name] = self.FakeWiki(name, self)

        self.wikis[name].set_content(content, author)

    def add_submission(self, submission):
        self.submissions.append(submission)

    def set_flairs(self, flair_list):
        self.sub_flairs = flair_list

class FakeSubmission():

    class FakeFlair():
        def __init__(self, flair_list, submission):
            self.flair_list = flair_list
            self.submission = submission
            self.set_flair_id = None

        def choices(self):
            for flair in self.flair_list:
                yield \
                {
                    "flair_css_class": flair,
                    "flair_template_id": flair
                }

        def select(self, flair_id):
            self.set_flair_id = flair_id

    crt_id = 0 # static member to keep track of the global submission ID

    def __init__(self, subreddit_name, author_name, title, body=None, url=None):
        self.id = base36.dumps(FakeSubmission.crt_id)
        self.shortlink = "https://redd.it/" + self.id
        self.created_utc = utils.utcnow()
        self.body = body
        self.url = url

        self.selftext = ""
        if body:
            self.selftext = body

        self.domain = "self"
        if self.url:
            self.domain = self.url.split("//")[1].split("/")[0].replace("www.", "")

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

        self.reports = []

        self.flairs = None
        # Create a flair instance for each submission
        if self.subreddit.sub_flairs:
            self.flairs = self.FakeFlair(self.subreddit.sub_flairs, self)

    @property
    def flair(self):
        return self.flairs

    @property
    def is_self(self):
        if self.body:
            return True
        return False

    def delete_by_author(self):
        self.author = None

    def delete_by_mod(self):
        self.is_crosspostable = False

    def set_link_flair_text(self, link_flair_text):
        self.link_flair_text = link_flair_text

    def report(self, reason):
        self.reports.append(reason)

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

class FakeURL():
    def __init__(self, url, title):
        self.url = url
        self.title = title

        cache_urls[url] = title

def create_bot(test_subreddit):
    """
    Bring up bot logic
    """
    # Clean up storage
    clean_storage_loc("storage_test/")
    set_storage_loc("storage_test/")

    # Set subreddit where the bot is a moderator
    set_moderated_subs([test_subreddit])

    # Create the bot
    bot(bot_config_path="tests/test-bot.ini", backend="test")

    # Feed an initial submission
    set_initial_sub(FakeSubmission(subreddit_name=test_subreddit, author_name="JohnDoe1", title="title1"))

    # Start up and wait for a while
    advance_time_10m()

    # Create more empty submissions
    FakeSubmission(subreddit_name=test_subreddit, author_name="JohnDoe1", title="title2")
    FakeSubmission(subreddit_name=test_subreddit, author_name="JohnDoe1", title="title3")

    # Update last seen submission
    new_all_sub(FakeSubmission(subreddit_name=test_subreddit, author_name="JohnDoe1", title="title4"))

    # Create more empty submissions
    FakeSubmission(subreddit_name=test_subreddit, author_name="JohnDoe1", title="title5")
    FakeSubmission(subreddit_name=test_subreddit, author_name="JohnDoe1", title="title6")

    # Wait again for things to settle
    advance_time_10m()

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
    time_trigger(utils.utcnow())

def advance_time_30s():
    for _ in range(30):
        do_tick()
        advance_time(1)

def advance_time_60s():
    for _ in range(60):
        do_tick()
        advance_time(1)

def advance_time_10m():
    for _ in range(60*10):
        do_tick()
        advance_time(1)

def advance_time_30m():
    for _ in range(60*30):
        do_tick()
        advance_time(1)

def advance_time_1h():
    for _ in range(60*60):
        do_tick()
        advance_time(1)

def set_moderated_subs(lst):
    global moderated_subs
    moderated_subs = lst