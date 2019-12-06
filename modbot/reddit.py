import traceback
import threading
import praw, prawcore
import time
import base36
from modbot.log import botlog
from modbot.utils import utcnow, timedata
from modbot.storage import dsdict, dsobj

logger = botlog("redditif")
watch_dict = {} # maps watched subreddits to threads

praw_credentials = None
praw_user_agent = None
praw_inst = {} # Dictionary of praw sessions
all_data = dsobj("all", "last_seen") # Last seen /r/all subs and comms
subreddit_cache = {}

wiki_storages = {}

last_wiki_update = utcnow()
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

        # Check if the subreddit has a wiki storage
        if self.subreddit_name not in wiki_storages:
            wiki_storages[self.subreddit_name] = dsdict(self.subreddit_name, "wiki_cache")

        storage = wiki_storages[self.subreddit_name]
        storage[self.name] = {
            "store_date": utcnow(),
            "subreddit": self.subreddit_name,
            "name": self.name,
            "content": self.content}

        storage.sync()

    def edit(self, content):
        get_subreddit(self.subreddit_name)._raw.wiki[self.name].edit(content)

    def get_content(self):
        return self.content

class wiki_stored(wiki):
    def __init__(self, storobj):
        self.subreddit_name = storobj["subreddit"]
        self.content = storobj["content"]
        self.name = storobj["name"]

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
                self.wikis[name] = wiki(self._raw.wiki[name])

        return self.wikis[name]

class user():
    """
    Class that encapsulates a PRAW user
    """
    def __init__(self, reddit_user):
        self._raw = reddit_user

    def __repr__(self):
        return self._raw.name

    def send_pm(self, subject, text, skip_signature=False):
        logger.debug("[%s] Send PM: %s / %s" % (self, subject, text))

        if not skip_signature:
            text += "\n\n***\n^^This ^^message ^^was ^^sent ^^by ^^a ^^bot. ^^For ^^more ^^details [^^send ^^a ^^message](https://www.reddit.com/message/compose?to=programatorulupeste&subject=Bot&message=) ^^to ^^its ^^author."

        self._raw.message(subject, text)

def set_praw_opts(credentials, user_agent):
    """
    Set authentication options
    """
    global praw_credentials
    global praw_user_agent

    praw_credentials = credentials
    praw_user_agent = user_agent

    # Start watching /r/all as soon as credentials are set
    watch_all()

def get_praw(name="default", force_create=False):
    """
    Get PRAW instance
    """
    def create_session():
        inst = None
        if praw_credentials and praw_user_agent:
            logger.debug("Creating PRAW instance")
            inst = praw.Reddit(praw_credentials, user_agent=praw_user_agent)
        else:
            raise ValueError("PRAW credentials not set")

        return inst

    global praw_inst

    if not force_create:
        if name in praw_inst:
            return praw_inst[name]

    praw_inst[name] = create_session()

    return praw_inst[name]

def get_subreddit(name):
    """
    Return subreddit instance
    """
    if name not in subreddit_cache:
        logger.debug("Added sub %s to cache" % name)
        subreddit_cache[name] = subreddit(get_praw().subreddit(name))

    return subreddit_cache[name]

def get_moderated_subs():
    """
    Get list of moderated subreddits
    """
    for i in get_praw().user.moderator_subreddits():
        if i.display_name.startswith("u_"):
            continue

        yield i.display_name

def get_submission(url):
    return submission(get_praw().submission(url=url))

def new_all_sub(sub):
    """
    Mark that a new submission has been seen
    """
    # Set last seen ID
    all_data.sub_seen_str = sub.id
    all_data.sub_seen_int = base36.loads(sub.id)

    # Check if it has
    if hasattr(all_data, "sub_fed_int") is False:
        all_data.sub_fed_int = all_data.sub.sub_seen_int
        return

    for sub_num in range(all_data.sub_fed_int + 1, all_data.sub_seen_int):
        all_data.sub_fed_int = sub_num

def new_all_comm(comm):
    """
    Mark that a new comment has been seen
    """
    # Set last seen ID
    all_data.comm_seen_str = comm.id
    all_data.comm_seen_int = base36.loads(comm.id)

    if hasattr(all_data, "comm_fed_int") is False:
        all_data.comm_fed_int = all_data.comm_seen_int
        return

    for comm_num in range(all_data.comm_fed_int + 1, all_data.comm_seen_int):
        all_data.comm_fed_int = comm_num
        print(get_praw().info("t1" + base36.dumps(comm_num)))

def thread_sub():
    """
    Watch submissions and trigger submission events

    :param subreddit: subreddit to watch
    """

    while True:
        session = get_praw("submissions_all")
        try:
            for sub in session.subreddit("all").stream.submissions(pause_after=None, skip_existing=True):
                new_all_sub(submission(sub))

        except (praw.exceptions.PRAWException, prawcore.exceptions.PrawcoreException) as e:
            print('PRAW exception ' + str(e))
            session = get_praw("submissions_all", True)

        except Exception:
            import traceback; traceback.print_exc()

        # If a loop happens, sleep for a bit
        time.sleep(0.1)

def thread_comm():
    """
    Watch comments and trigger comments events

    :param subreddit: subreddit to watch
    """

    while True:
        session = get_praw("comments_all")
        try:
            for comm in session.subreddit("all").stream.comments(pause_after=None, skip_existing=True):
                new_all_comm(comment(comm))

        except (praw.exceptions.PRAWException, prawcore.exceptions.PrawcoreException) as e:
            print('PRAW exception ' + str(e))
            session = get_praw("comments_all", True)

        except Exception:
            import traceback; traceback.print_exc()

        # If a loop happens, sleep for a bit
        time.sleep(0.1)

def watch_all():
    logger.debug("Watching all")

    sthread = threading.Thread(
            name="submissions_all",
            target = thread_sub)
    sthread.setDaemon(True)
    sthread.start()

    cthread = threading.Thread(
            name="comments_all",
            target = thread_comm)
    cthread.setDaemon(True)
    cthread.start()

def watch_sub(subreddit_name, callback_sub, callback_comm):
    pass

def update_all_wikis(tnow):
    global wiki_update_thread
    global last_wiki_update

    def update_wikis():
        logger.debug("Starting wiki update")
        for sub in subreddit_cache.values():
            logger.debug("Updating %s" % sub)
            for wiki_name in sub.wikis:
                sub.wikis[wiki_name] = wiki(sub._raw.wiki[wiki_name])

        logger.debug("Done wiki update")

    if wiki_update_thread and wiki_update_thread.isAlive():
        return

    if tnow - last_wiki_update < WIKI_UPDATE_INTERVAL:
        return

    last_wiki_update = tnow
    wiki_update_thread = threading.Thread(
            name="wiki updater",
            target=update_wikis)
    wiki_update_thread.setDaemon(True)
    wiki_update_thread.start()

def start_tick(period, call_per):
    def tick():
        while True:
            # Sleep for the given period
            time.sleep(period)

            tnow = utcnow()
            try:
                update_all_wikis(tnow)
                call_per(tnow)
            except:
                import traceback; traceback.print_exc()

    logger.debug("Starting periodic check thread with %f interval" % period)
    periodic_thread = threading.Thread(
            name="periodic_thread",
            target=tick)

    periodic_thread.setDaemon(True)
    periodic_thread.start()
