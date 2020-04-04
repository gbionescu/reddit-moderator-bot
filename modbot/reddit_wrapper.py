import traceback
import time
import base36
import importlib
from modbot.log import botlog, loglevel
from modbot.utils import utcnow, timedata, BotThread, get_utcnow
from modbot.storage import dsdict, get_stored_dict
from modbot.input.rpc_server import create_server

logger = botlog("reddit_wrapper", console_level=loglevel.DEBUG)
audit = botlog("audit", console_level=loglevel.DEBUG)
watch_dict = {}  # maps watched subreddits to threads

posted_things_body = get_stored_dict("all", "posted")

backend = None
all_data = None
subreddit_cache = None
wiki_storages = None
sub_feeder = None
com_feeder = None
bot_signature = None
inbox_thread = None
last_inbox_update = None
report_cmds = None
cache_data = None
modlog_hist = None

last_moderator_subs_check = 0
moderator_subs_list = []

COLD_WIKI_LIMIT = timedata.SEC_IN_MIN
update_intervals = {
    "inbox_update": 10,
    "moderated_subs": timedata.SEC_IN_MIN * 30,
    "moderator_users": timedata.SEC_IN_MIN * 30
}


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
        try:
            return get_subreddit(self._raw.subreddit.display_name)
        except:
            logger.debug("Could not get subreddit %s" %
                         self._raw.subreddit.display_name)

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
        try:
            if self._raw.author:
                return user(self._raw.author)
            else:
                return None
        except:
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
        audit.debug("[%s] Reported with reason: %s" % (self, reason))
        self._raw.report(reason)

    @property
    def flair(self):
        return self._raw.flair

    @property
    def selftext(self):
        return self._raw.selftext

    def edit(self, body):
        if self.shortlink in posted_things_body and \
                body == posted_things_body[self.shortlink]:
            return

        posted_things_body[self.shortlink] = body
        self._raw.edit(body)

    @property
    def stickied(self):
        return self._raw.stickied

    def make_sticky(self):
        self._raw.mod.sticky(state=True, bottom=True)


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

    @property
    def permalink(self):
        return self._raw.permalink

    @property
    def body(self):
        return self._raw.body

    @property
    def author(self):
        return self._raw.author


class wiki():
    def __init__(self, reddit_wiki):
        try:
            self.content = reddit_wiki.content_md
        except:
            self.content = ""

        # Set permissions to mod only
        try:
            reddit_wiki.mod.update(listed=False, permlevel=2)
        except:
            pass

        self.subreddit_name = reddit_wiki.subreddit.display_name
        self.name = reddit_wiki.name

        try:
            self.author = user(reddit_wiki.revision_by)
        except:
            self.author = ""

        try:
            self.revision_date = int(reddit_wiki.revision_date)
        except:
            self.revision_date = 0

        # Check if the subreddit has a wiki storage
        if self.subreddit_name not in wiki_storages:
            logger.debug("Adding %s/%s to wiki storage" %
                         (self.subreddit_name, self.name))
            wiki_storages[self.subreddit_name] = dsdict(
                self.subreddit_name, "wiki_cache")

        storage = wiki_storages[self.subreddit_name]
        storage[self.name] = {
            "store_date": utcnow(),
            "subreddit": self.subreddit_name,
            "name": self.name,
            "content": self.content,
            "author": str(self.author),
            "revision_date": self.revision_date}

        storage.sync()

    def edit(self, content):
        backend.edit_wiki(get_subreddit(
            self.subreddit_name)._raw, self.name, content)

    def get_content(self):
        return self.content


class wiki_stored(wiki):
    def __init__(self, storobj):
        self.subreddit_name = storobj["subreddit"]
        self.content = storobj["content"]
        self.name = storobj["name"]
        self.author = get_user(storobj["author"])
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

    def send_modmail(self, subject, text, skip_signature=False):
        if not skip_signature and bot_signature:
            text += bot_signature
        audit.debug("[%s] Send modmail: %s / %s" % (self, subject, text))
        self._raw.message(subject, text)

    def wiki(self, name, force_live=False):
        if force_live:
            logger.debug("Getting a fresh copy of %s/%s" %
                         (self.display_name, name))
            self.wikis[name] = wiki(backend.get_wiki(self._raw, name))

        logger.debug("[%s] Access wiki: %s" % (self, name))

        if str(self) not in wiki_storages:
            wiki_storages[str(self)] = dsdict(str(self), "wiki_cache")

        # Check if there is a copy of the wiki stored
        if name in wiki_storages[str(self)] and \
                utcnow() - wiki_storages[str(self)][name]["store_date"] < COLD_WIKI_LIMIT:

            logger.debug("Getting stored copy of %s/%s" %
                         (self.display_name, name))
            self.wikis[name] = wiki_stored(wiki_storages[str(self)][name])
        else:
            logger.debug("Getting a fresh copy of %s/%s" %
                         (self.display_name, name))
            self.wikis[name] = wiki(backend.get_wiki(self._raw, name))

        return self.wikis[name]

    def stylesheet_upload_image(self, name, local_path):
        return self._raw.stylesheet.upload(name, local_path)

    def stylesheet_get_content(self):
        return self._raw.stylesheet().stylesheet

    def stylesheet_set_content(self, content):
        return self._raw.stylesheet.update(content)

    def get_sidebar_widgets(self):
        items = []
        for w in self._raw.widgets.sidebar:
            items.append(widget(w))

        return items


class widget():
    def __init__(self, widget):
        self._raw = widget
        self.name = widget.shortName
        self.kind = widget.kind
        self.subreddit = subreddit

    def set_image(self, path, picture_link):
        upload_url = self._raw.subreddit.widgets.mod.upload_image(path)

        new_data = {}
        new_data["width"] = 0
        new_data["height"] = 0
        new_data["linkUrl"] = picture_link
        new_data["url"] = upload_url

        self._raw.mod.update(data=[new_data])


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
        # Don't send message to self
        if self._raw.name == backend.get_reddit().user.me().name:
            return
        audit.debug("[%s] Send PM: %s / %s" % (self, subject, text))

        if not skip_signature and bot_signature:
            text += bot_signature

        self._raw.message(subject, text)

    @property
    def name(self):
        return self.username


class inboxmessage():
    """
    Encapsulate an inbox message
    """

    def __init__(self, msg):
        self._raw = msg
        self.body = msg.body
        self.author = user(msg.author)


class report():
    """
    Encapsulate a report
    """

    def __init__(self, item, author, body):
        self._raw = item
        self.author = author
        self.body = body
        self.permalink = item.permalink

    @property
    def author_name(self):
        return self._raw.author.name

    @property
    def subreddit_name(self):
        return self._raw.subreddit.display_name


class BotFeeder():
    """
    Feeds submissions or comments to a given function
    """

    def __init__(self, storage, objtype, callback, objclass, max_workers, items_per_worker):
        self.objtype = objtype
        self.storage = storage

        storage[self.objtype] = {}
        self.storchild = storage[objtype]
        self.callback = callback
        self.objclass = objclass

        self.max_workers = max_workers
        self.items_per_worker = items_per_worker
        self.worker_processing = False

        # Initialize empty members
        self.storchild["pending"] = 0
        self.storchild["seen"] = 0
        self.storchild["fed"] = 0
        self.storchild["workers"] = []
        self.storage.sync()

    def set_all_object(self, name, obj, dosync=True):
        """
        Set a generic object in storage
        """
        if self.objtype not in self.storage:
            self.storage[self.objtype] = {}

        self.storchild[name] = base36.loads(obj.id)

        # Check if we should sync the data
        if dosync:
            self.storage.sync()

    def set_initial(self, obj):
        """
        Initialize storage
        """
        self.set_all_object("init", obj, False)
        self.set_all_object("fed", obj, False)
        self.set_all_object("pending", obj)

    def new_all_object(self, obj):
        """
        Mark that a new object has been seen on /r/all
        """
        self.set_all_object("seen", obj)
        self.storchild["drift"] = self.storchild["seen"] - \
            self.storchild["fed"]

    def create_new_worker(self):
        """
        Create a new worker to feed items to the bot
        """

        # If there is a difference in seen vs. pending items
        if self.storchild["seen"] - self.storchild["pending"] <= 0:
            return

        if len(self.storchild["workers"]) < self.max_workers:
            new_obj = {}
            new_obj["start"] = self.storchild["pending"] + 1
            new_obj["end"] = min(self.storchild["seen"],
                                 new_obj["start"] + self.items_per_worker)
            new_obj["finished"] = 0

            self.storchild["workers"].append(new_obj)
            self.storchild["pending"] = new_obj["end"]
            #print("Start: %d -> %d" % (new_obj["start"], new_obj["end"]))
            #print("Pending %d, Fed %d\n" % (self.storchild["pending"], self.storchild["fed"]))
            self.storage.sync()

            BotThread(
                name="ketchup_thread",
                target=self.catch_up,
                args=(new_obj,))

    def clean_up_finished(self):
        """
        Clean up finished workers
        """
        changed = False
        # The first element should always be the one that should be consumed
        while len(self.storchild["workers"]) > 0 and self.storchild["workers"][0]["finished"] == 1:
            changed = True
            element = self.storchild["workers"][0]

            self.storchild["fed"] = element["end"]
            self.storchild["drift"] = self.storchild["seen"] - \
                self.storchild["fed"]
            self.storchild["workers"] = self.storchild["workers"][1:]
            #print("Ended: %d -> %d" % (element["start"], element["end"]))
            #print("Pending %d, Fed %d\n" % (self.storchild["pending"], self.storchild["fed"]))

        if changed:
            self.storage.sync()

    def feed_new_elements(self):
        """
        Trigger creation/cleanup of workers
        """
        if self.worker_processing:
            return

        try:
            self.worker_processing = True
            self.create_new_worker()
            self.clean_up_finished()
        except:
            import traceback
            traceback.print_exc()
        finally:
            self.worker_processing = False

    def catch_up(self, worker):
        """
        Worker that feeds data to the bot
        """
        obj_list = []
        obj_gen = None
        for num in range(worker["start"], worker["end"] + 1):
            obj_list.append(self.objtype + base36.dumps(num))

        obj_gen = backend.get_reddit().info(obj_list)

        # returns a generator
        for obj in obj_gen:
            if self.callback:
                try:
                    self.callback(self.objclass(obj))
                except:
                    import traceback
                    traceback.print_exc()
            self.storage.sync()

        worker["finished"] = 1
        self.storage.sync()


class CacheData():
    """
    Holds information about a cached object - whether it's time to update it or not
    """

    def __init__(self, interval):
        self.interval = interval
        self.last_check = -1000000
        self.opaque = None

    def expired(self):
        if utcnow() - self.last_check > self.interval:
            return True
        return False

    def set_opaque(self, opaque):
        self.opaque = opaque

    def mark_updated(self):
        self.last_check = utcnow()


class modlog():
    def __init__(self, modlog_item):
        self._raw = modlog_item
        self.mod_name = self._raw.mod.name
        self.target_author = self._raw.target_author
        self.details = self._raw.details
        self.description = self._raw.description
        self.subreddit_name = self._raw.subreddit
        self.action = self._raw.action
        self.target_permalink = self._raw.target_permalink


def is_expired(name):
    """
    Check if a cached object has expired
    """
    if name not in cache_data:
        cache_data[name] = CacheData(update_intervals[name])

    return cache_data[name].expired()


def set_input_type(input_type):
    global backend
    global all_data
    global wiki_storages
    global subreddit_cache
    global report_cmds
    global cache_data
    global modlog_hist

    backend = importlib.import_module("modbot.input.%s" % input_type)

    # Initialize objects that depend on the backend
    all_data = dsdict("all", "last_seen")  # Last seen /r/all subs and comms
    wiki_storages = {}
    subreddit_cache = {}
    cache_data = {}
    report_cmds = dsdict("mod", "cmds")
    modlog_hist = dsdict("mod", "modlog")


def set_credentials(credentials, user_agent):
    audit.debug("Credentials set")
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
    if name:
        return user(backend.get_reddit().redditor(name))
    return None


def get_moderated_subs():
    """
    Get list of moderated subreddits
    """
    if not is_expired("moderated_subs"):
        return cache_data["moderated_subs"].opaque

    moderator_subs_list = []
    for i in backend.get_reddit().user.moderator_subreddits():
        if i.display_name.startswith("u_"):
            continue

        moderator_subs_list.append(i.display_name)

    cache_data["moderated_subs"].set_opaque(moderator_subs_list)
    cache_data["moderated_subs"].mark_updated()
    return moderator_subs_list


def get_moderator_users():
    """
    Returns list of moderators where the bot is also a mod
    """
    if not is_expired("moderator_users"):
        return cache_data["moderator_users"].opaque

    mod_list = []
    for sub in get_moderated_subs():
        for mod in backend.get_reddit().subreddit(sub).moderator():
            mod_list.append(str(mod))

    cache_data["moderator_users"].set_opaque(list(set(mod_list)))
    cache_data["moderator_users"].mark_updated()
    return cache_data["moderator_users"].opaque

def get_moderators_for_sub(sub):
    """
    Returns a list of mods for a subreddit
    """
    mods = []

    sub = backend.get_reddit().subreddit(sub)
    for mod in sub.moderator():
        mods.append(str(mod))

    return mods


def get_comment(id):
    return comment(backend.get_reddit().comment(id=id))


def get_submission(url):
    return submission(backend.get_reddit().submission(url=url))

def format_string(to_format):
    date = get_utcnow()

    to_format = to_format.replace(r"${DAY}", str(date.day).zfill(2))
    to_format = to_format.replace(r"${MONTH}", str(date.month).zfill(2))
    to_format = to_format.replace(r"${YEAR}", str(date.year))

    return to_format


def post_submission_text(sub_name, title, body, sticky):
    post_subreddit = get_subreddit(sub_name)

    body = format_string(body)
    title = format_string(title)

    # TODO check if bot moderates sub
    posted = post_subreddit._raw.submit(
        title=title,
        selftext=body,
        send_replies=False)

    # Get the posted submission
    check_posted = get_submission(posted.shortlink)

    # Check if it was removed
    if not check_posted.is_crosspostable:
        try:
            posted.mod.approve()
        except:
            audit.error("Error approving post")

    if sticky:
        try:
            posted.mod.sticky(state=True, bottom=True)
        except:
            audit.error("Error stickying post")

    bot_posted = submission(posted)
    posted_things_body[bot_posted.shortlink] = body
    return bot_posted


def new_report(item, author, body):
    """
    Check if an item can be added in the report feeder
    """
    def add_item():
        if item.id not in report_cmds:
            report_cmds[item.id] = {}

        if "/created_utc" not in report_cmds[item.id]:
            report_cmds[item.id]["/created_utc"] = item.created_utc

        if author not in report_cmds[item.id]:
            report_cmds[item.id][author] = [body]
        else:
            report_cmds[item.id][author].append(body)
        report_cmds.sync()

    if not author:
        return

    # If the item is older than a week, ignore it
    if utcnow() - item.created_utc > timedata.SEC_IN_WEEK:
        return

    # Clean up items older than a week
    for key, val in report_cmds.items():
        if utcnow() - val["/created_utc"] > timedata.SEC_IN_WEEK:
            del report_cmds[key]
            report_cmds.sync()

    new_item = False
    # If the item wasn't there before, add it
    if item.id not in report_cmds:
        new_item = True
        add_item()

    # If the reporter was not there before, add it
    if not new_item and author not in report_cmds[item.id]:
        new_item = True
        add_item()

    # If the report reason was not there before, add it
    if not new_item and body not in report_cmds[item.id][author]:
        new_item = True
        add_item()

    if new_item:
        report_feeder(report(item, get_user(author), body))


def new_modlog_item(item):
    if item.id not in modlog_hist:
        modlog_hist[item.id] = item.created_utc
        modlog_feeder(modlog(item))

    to_delete = []
    for key, val in modlog_hist.items():
        if utcnow() - val > timedata.SEC_IN_DAY * 7:
            to_delete.append(key)

    for key in to_delete:
        del modlog_hist[key]


def watch_all(sub_func, comm_func, inbox_func, report_func, modlog_func):
    global sub_feeder
    global com_feeder
    global inbox_feeder
    global report_feeder
    global modlog_feeder
    global rpc_server

    # Initialize feeder classes
    sub_feeder = BotFeeder(all_data, "t3_", sub_func, submission, 10, 99)
    com_feeder = BotFeeder(all_data, "t1_", comm_func, comment, 10, 99)

    inbox_feeder = inbox_func
    report_feeder = report_func
    modlog_feeder = modlog_func

    logger.debug("Watching all")
    BotThread(
        name="submissions_all",
        target=backend.thread_sub,
        args=(sub_feeder,))

    BotThread(
        name="comments_all",
        target=backend.thread_comm,
        args=(com_feeder,))

    BotThread(
        name="reports_mod",
        target=backend.thread_reports,
        args=(new_report,))

    BotThread(
        name="modlog_thread",
        target=backend.thread_modlog,
        args=(new_modlog_item,))

    # Create RPC server
    rpc_server = create_server(inbox_func)


def check_inbox(tnow):
    """
    Check the inbox for updates
    """
    def _check_inbox():
        # For each unread message
        for message in backend.get_reddit().inbox.unread(limit=None):
            if inbox_feeder:
                # Mark message as read
                message.mark_read()

                # Give it to the bot
                if message.author:
                    inbox_feeder(inboxmessage(message))

    global inbox_thread
    if inbox_thread and inbox_thread.isAlive():
        return

    if not is_expired("inbox_update"):
        return

    inbox_thread = BotThread(
        _check_inbox,
        "inbox_thread")
    cache_data["inbox_update"].mark_updated()


def start_tick(period, call_per):
    def tick(tnow):
        try:
            check_inbox(tnow)

            # Check if we can feed new elements
            if sub_feeder:
                sub_feeder.feed_new_elements()

            if com_feeder:
                com_feeder.feed_new_elements()

            # Call periodic callback
            call_per(tnow)
        except:
            import traceback
            traceback.print_exc()

    logger.debug("Starting periodic check thread with %f interval" % period)
    BotThread(
        name="periodic_thread",
        target=backend.tick,
        args=(period, tick,))


def set_signature(signature):
    global bot_signature
    bot_signature = signature
