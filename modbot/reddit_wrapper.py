import traceback
import time
import base36
import logging
import importlib
from modbot.log import botlog
from modbot.utils import utcnow, timedata, BotThread
from modbot.storage import dsdict, dsobj

logger = botlog("reddit_wrapper", console=logging.DEBUG)
watch_dict = {} # maps watched subreddits to threads

bot_sub_hook = None
bot_comm_hook = None
backend = None
all_data = None
subreddit_cache = None
wiki_storages = None
last_wiki_update = None
wiki_update_thread = None

WIKI_UPDATE_INTERVAL = timedata.SEC_IN_MIN
COLD_WIKI_LIMIT = timedata.SEC_IN_MIN * 15

class submission():
    """
    Class that encapsulates a PRAW submission
    """
    def __init__(self, reddit_sub):
        self._raw = reddit_sub

    def __repr__(self):
        return self._raw.shortlink

    def set_flair_id(self, flair_id):
        logger.debug("[%s] Set flair id: %s" % (self, flair_id))
        self._raw.flair.select(flair_id)

    @property
    def subreddit_name(self):
        return self._raw.subreddit.display_name

    @property
    def subreddit(self):
        return get_subreddit(self._raw.subreddit.display_name)

    @property
    def shortlink(self):
        return self._raw.shortlink

    @property
    def title(self):
        return self._raw.title

    @property
    def created_utc(self):
        return self._raw.created_utc

    @property
    def author(self):
        if self._raw.author:
            return user(self._raw.author)
        else:
            return None

    @property
    def is_crosspostable(self):
        return self._raw.is_crosspostable

    @property
    def is_self(self):
        return self._raw.is_self

    @property
    def url(self):
        return self._raw.url

    @property
    def link_flair_text(self):
        return self._raw.link_flair_text

    @property
    def domain(self):
        return self._raw.domain

    @property
    def id(self):
        return self._raw.id

    def report(self, reason):
        logger.debug("[%s] Reported with reason: %s" % (self, reason))
        self._raw.report(reason)

    @property
    def flair(self):
        return self._raw.flair

    @property
    def selftext(self):
        return self._raw.selftext

class comment():
    """
    Class that encapsulates a PRAW comment
    """
    def __init__(self, reddit_comm):
        self._raw = reddit_comm

    @property
    def subreddit_name(self):
        return self._raw.subreddit.display_name

    @property
    def subreddit(self):
        return get_subreddit(self._raw.subreddit.display_name)

    @property
    def id(self):
        return self._raw.id

class wiki():
    def __init__(self, reddit_wiki):
        self.content = reddit_wiki.content_md
        self.subreddit_name = reddit_wiki.subreddit.display_name
        self.name = reddit_wiki.name
        self.author = user(reddit_wiki.revision_by)
        self.revision_date = int(reddit_wiki.revision_date)

        # Check if the subreddit has a wiki storage
        if self.subreddit_name not in wiki_storages:
            wiki_storages[self.subreddit_name] = dsdict(self.subreddit_name, "wiki_cache")

        storage = wiki_storages[self.subreddit_name]
        storage[self.name] = {
            "store_date": utcnow(),
            "subreddit": self.subreddit_name,
            "name": self.name,
            "content": self.content,
            "author": self.author.name,
            "revision_date": self.revision_date}

        storage.sync()

    def edit(self, content):
        backend.edit_wiki(get_subreddit(self.subreddit_name)._raw, self.name, content)

    def get_content(self):
        return self.content

class wiki_stored(wiki):
    def __init__(self, storobj):
        self.subreddit_name = storobj["subreddit"]
        self.content = storobj["content"]
        self.name = storobj["name"]
        self.author = user(get_user(storobj["author"]))
        self.revision_date = int(storobj["revision_date"])

class subreddit():
    """
    Class that encapsulates a PRAW subreddit
    """
    def __init__(self, reddit_sub):
        self._raw = reddit_sub
        self.wikis = {}

    def __repr__(self):
        return self._raw.display_name

    def __eq__(self, string):
        return self._raw.display_name == string

    @property
    def display_name(self):
        return self._raw.display_name

    @property
    def subreddit_type(self):
        return self._raw.subreddit_type

    def is_private(self):
        if "private" in self.subreddit_type:
            return True

        return False

    def wiki(self, name):
        if name not in self.wikis:
            logger.debug("[%s] Access wiki: %s" % (self, name))

            if str(self) not in wiki_storages:
                wiki_storages[str(self)] = dsdict(str(self), "wiki_cache")

            # Check if there is a copy of the wiki stored
            if name in wiki_storages[str(self)] and \
                utcnow() - wiki_storages[str(self)][name]["store_date"] < COLD_WIKI_LIMIT:

                self.wikis[name] = wiki_stored(wiki_storages[str(self)][name])
            else:
                self.wikis[name] = wiki(backend.get_wiki(self._raw, name))

        return self.wikis[name]

class user():
    """
    Class that encapsulates a PRAW user
    """
    def __init__(self, reddit_user):
        self._raw = reddit_user
        self.username = reddit_user.name

    def __repr__(self):
        return self._raw.name

    def send_pm(self, subject, text, skip_signature=False):
        logger.debug("[%s] Send PM: %s / %s" % (self, subject, text))

        if not skip_signature:
            text += "\n\n***\n^^This ^^message ^^was ^^sent ^^by ^^a ^^bot. ^^For ^^more ^^details [^^send ^^a ^^message](https://www.reddit.com/message/compose?to=programatorulupeste&subject=Bot&message=) ^^to ^^its ^^author."

        self._raw.message(subject, text)

    @property
    def name(self):
        return self.username

def set_input_type(input_type):
    global backend
    global all_data
    global wiki_storages
    global subreddit_cache
    global last_wiki_update
    global bot_sub_hook
    global bot_comm_hook
    global wiki_update_thread

    backend = importlib.import_module("modbot.input.%s" % input_type)

    # Initialize objects that depend on the backend
    all_data = dsobj("all", "last_seen") # Last seen /r/all subs and comms
    wiki_storages = {}
    subreddit_cache = {}
    last_wiki_update = utcnow()
    bot_sub_hook = None
    bot_comm_hook = None
    wiki_update_thread = None

def set_credentials(credentials, user_agent):
    backend.set_praw_opts(credentials, user_agent)

def get_subreddit(name):
    """
    Return subreddit instance
    """
    if name not in subreddit_cache:
        logger.debug("Added sub %s to cache" % name)
        subreddit_cache[name] = subreddit(backend.get_reddit().subreddit(name))

    return subreddit_cache[name]

def get_user(name):
    return backend.get_reddit().redditor(name)

def get_moderated_subs():
    """
    Get list of moderated subreddits
    """
    for i in backend.get_reddit().user.moderator_subreddits():
        if i.display_name.startswith("u_"):
            continue

        yield i.display_name

def get_submission(url):
    return submission(backend.get_reddit().submission(url=url))

def set_initial_submission(sub):
    """
    Set the initial submission ID
    """

    logger.debug("Set first submission id to " + sub.id)
    all_data.sub_init_str = sub.id
    all_data.sub_init_int = base36.loads(sub.id)

    set_fed_submission(sub)

def set_fed_submission(sub):
    """
    Set the last fed submission ID
    """

    # Feed it to the bot
    if bot_sub_hook:
        bot_sub_hook(submission(sub))

    all_data.sub_fed_str = sub.id
    all_data.sub_fed_int = base36.loads(sub.id)

def set_seen_submission(sub):
    """
    Set the last seen submission ID
    """
    all_data.sub_seen_str = sub.id
    all_data.sub_seen_int = base36.loads(sub.id)

def new_all_sub(sub):
    """
    Mark that a new submission has been seen
    """
    # Set last seen
    set_seen_submission(sub)

    for sub_num in range(all_data.sub_fed_int + 1, all_data.sub_seen_int + 1):
        sub = get_submission("https://redd.it/" + base36.dumps(sub_num))
        #print("Feeding new sub " + str(sub.id))
        set_fed_submission(sub)

def set_initial_comment(comm):
    """
    Set initial comment
    """

    logger.debug("Set first comment id to " + comm.id)
    all_data.comm_init_str = comm.id
    all_data.comm_init_id = base36.loads(comm.id)

    set_fed_comment(comm)

def set_fed_comment(comm):
    """
    Set the last fed comment ID
    """

    # Feed it to the bot
    if bot_comm_hook:
        bot_comm_hook(comment(comm))

    all_data.comm_fed_str = comm.id
    all_data.comm_fed_int = base36.loads(comm.id)

def set_seen_comment(comm):
    """
    Set the last fed comment ID
    """
    all_data.comm_seen_str = comm.id
    all_data.comm_seen_int = base36.loads(comm.id)

def new_all_comm(comm):
    """
    Mark that a new comment has been seen
    """
    # Set last seen ID
    set_seen_comment(comm)

    comm_list = []
    comm_gen = None
    for comm_num in range(all_data.comm_fed_int + 1, all_data.comm_seen_int):
        comm_list.append("t1_" + base36.dumps(comm_num))
        comm_gen = backend.get_reddit().info(comm_list)

    if not comm_gen:
        return

    # get_praw returns a generator
    for comm in comm_gen:
        #print("Feeding new comment " + str(comm.id))
        set_fed_comment(comm)

def watch_all(sub_func, comm_func):
    global bot_sub_hook
    global bot_comm_hook

    bot_sub_hook = sub_func
    bot_comm_hook = comm_func

    logger.debug("Watching all")

    sthread = BotThread(
            name="submissions_all",
            target = backend.thread_sub,
            args=(set_initial_submission, new_all_sub,))
    sthread.setDaemon(True)
    sthread.start()

    cthread = BotThread(
            name="comments_all",
            target = backend.thread_comm,
            args=(set_initial_comment, new_all_comm,))
    cthread.setDaemon(True)
    cthread.start()

def update_all_wikis(tnow):
    global wiki_update_thread
    global last_wiki_update

    def update_wikis():
        logger.debug("Starting wiki update")
        for sub in subreddit_cache.values():
            logger.debug("Updating %s" % sub)
            for wiki_name in sub.wikis:
                sub.wikis[wiki_name] = wiki(backend.get_wiki(sub._raw, wiki_name))

        logger.debug("Done wiki update")

    if wiki_update_thread and wiki_update_thread.isAlive():
        return

    if tnow - last_wiki_update < WIKI_UPDATE_INTERVAL:
        return

    last_wiki_update = tnow
    wiki_update_thread = BotThread(
            name="wiki updater",
            target=update_wikis)
    wiki_update_thread.setDaemon(True)
    wiki_update_thread.start()

def start_tick(period, call_per):
    def tick(tnow):
        try:
            update_all_wikis(tnow)
            call_per(tnow)
        except:
            import traceback; traceback.print_exc()

    logger.debug("Starting periodic check thread with %f interval" % period)
    periodic_thread = BotThread(
            name="periodic_thread",
            target=backend.tick,
            args=(period, tick,))

    periodic_thread.setDaemon(True)
    periodic_thread.start()
