import praw
import prawcore
import time
import requests
import json
from modbot.log import botlog, loglevel
from modbot.utils import utcnow, timedata

praw_credentials = None
praw_user_agent = None
praw_inst = {}  # Dictionary of praw sessions
logger = botlog("redditinput", console_level=loglevel.DEBUG)
audit = botlog("audit", console_level=loglevel.DEBUG)
idfeeder = botlog("idfeeder", console_level=loglevel.DEBUG)


class Thing():
    """
    Thing class to mock reddit thing
    """

    def __init__(self, id):
        self.id = id


def set_praw_opts(credentials, user_agent):
    """
    Set authentication options
    """
    global praw_credentials
    global praw_user_agent

    praw_credentials = credentials
    praw_user_agent = user_agent


def get_reddit_object(url):
    """
    Gets a reddit json page and extracts the first thing ID
    """
    try:
        user_agent = praw_user_agent
        headers = {'User-Agent': user_agent}
        response = requests.get(url, headers=headers)
        data = json.loads(response.text)

        return data["data"]["children"][0]["data"]["id"]
    except:
        return None


def get_reddit(name="default", force_create=False):
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


def thread_sub(feeder):
    """
    Watch submissions and trigger submission events
    """
    def get_item():
        try:
            for sub in get_reddit().subreddit("all").stream.submissions(pause_after=0, skip_existing=True):
                return sub.id
        except:
            return None

    first_set = False
    logger.debug("Getting base submission")
    # Get one submission and set it as the initial one
    while not first_set:
        #sub_id = get_reddit_object("https://www.reddit.com/r/all/new.json")
        sub_id = get_item()
        if sub_id:
            idfeeder.debug("Feeding sub ID %s" % sub_id)
            feeder.set_initial(Thing(sub_id))
            first_set = True
        else:
            time.sleep(1)

    while True:
        # Do this every 30s
        time.sleep(30)

        # Feed all submissions
        #sub_id = get_reddit_object("https://www.reddit.com/r/all/new.json")
        sub_id = get_item()
        if sub_id:
            idfeeder.debug("Feeding sub ID %s" % sub_id)
            feeder.new_all_object(Thing(sub_id))


def thread_comm(feeder):
    """
    Watch comments and trigger comments events
    """

    # Disabled for now, as it caused the bot to do to many requests
    return
    first_set = False
    logger.debug("Getting base comment")
    # Get one comment and set it as the initial one
    while not first_set:
        comm_id = get_reddit_object(
            "https://www.reddit.com/r/all/comments.json")
        if comm_id:
            feeder.set_initial(Thing(comm_id))
            first_set = True
        else:
            time.sleep(1)

    while True:
        # Do this every 10s
        time.sleep(10)

        # Feed all submissions
        comm_id = get_reddit_object(
            "https://www.reddit.com/r/all/comments.json")
        feeder.new_all_object(Thing(comm_id))


def thread_reports(new_report):
    """
    Watch reports and trigger events
    """
    while True:
        session = get_reddit()
        try:
            # Feed all reports
            for reported_item in session.subreddit("mod").mod.reports():
                for mod_report in reported_item.mod_reports:
                    new_report(reported_item, mod_report[1], mod_report[0])

        except (praw.exceptions.PRAWException, prawcore.exceptions.PrawcoreException) as e:
            print('PRAW exception ' + str(e))
            session = get_reddit("reports", True)

        except Exception:
            import traceback
            traceback.print_exc()

        # If a loop happens, sleep for a bit
        time.sleep(5)


def thread_modlog(modlog_func):
    """
    Watch modlog and trigger events
    """
    while True:
        session = get_reddit()
        try:
            # Feed all modlog
            for log in session.subreddit('mod').mod.log():
                modlog_func(log)

        except (praw.exceptions.PRAWException, prawcore.exceptions.PrawcoreException) as e:
            print('PRAW exception ' + str(e))
            session = get_reddit("reports", True)

        except Exception:
            import traceback
            traceback.print_exc()

        # If a loop happens, sleep for a bit
        time.sleep(30)


def thread_modqueue(modlog_func, target='mod'):
    """
    Watch modlog and trigger events
    """
    while True:
        session = get_reddit()
        try:
            # Feed all modlog
            for item in session.subreddit(target).mod.modqueue():
                modlog_func(item)

        except (praw.exceptions.PRAWException, prawcore.exceptions.PrawcoreException) as e:
            print('PRAW exception ' + str(e))
            session = get_reddit("reports", True)

        except Exception:
            import traceback
            traceback.print_exc()

        # If a loop happens, sleep for a bit
        time.sleep(30)

def get_all_modqueue(target):
    session = get_reddit()
    try:
        # Feed all modlog
        for item in session.subreddit(target).mod.modqueue(limit=None):
            yield item

    except (praw.exceptions.PRAWException, prawcore.exceptions.PrawcoreException) as e:
        print('PRAW exception ' + str(e))

    except Exception:
        import traceback
        traceback.print_exc()

def get_wiki(subreddit, wiki_name):
    data = subreddit.wiki[wiki_name]
    logger.debug("[%s/%s] Got wiki content: %s" % (subreddit.display_name, wiki_name, data))
    return data


def edit_wiki(subreddit, wiki_name, content):
    logger.debug("[%s/%s] Edit wiki content: %s" % (subreddit.display_name, wiki_name, content))
    subreddit.wiki[wiki_name].edit(content)


def tick(period, trigger):
    while True:
        # Sleep for the given period
        time.sleep(period)

        tnow = utcnow()
        try:
            trigger(tnow)
        except:
            import traceback
            traceback.print_exc()
