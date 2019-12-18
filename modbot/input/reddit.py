import praw, prawcore
import logging
import time
from modbot.log import botlog
from modbot.utils import utcnow, timedata

praw_credentials = None
praw_user_agent = None
praw_inst = {} # Dictionary of praw sessions
logger = botlog("redditinput", console=logging.DEBUG)

def set_praw_opts(credentials, user_agent):
    """
    Set authentication options
    """
    global praw_credentials
    global praw_user_agent

    praw_credentials = credentials
    praw_user_agent = user_agent

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

def thread_sub(set_initial_submission, new_all_sub):
    """
    Watch submissions and trigger submission events

    :param subreddit: subreddit to watch
    """

    while True:
        session = get_reddit("submissions_all")
        logger.debug("Getting base submission")
        # Get one submission and set it as the initial one
        for sub in session.subreddit("all").stream.submissions(pause_after=None, skip_existing=True):
            set_initial_submission(sub)
            break

        try:
            # Feed all submissions
            for sub in session.subreddit("all").stream.submissions(pause_after=None, skip_existing=True):
                new_all_sub(sub)

        except (praw.exceptions.PRAWException, prawcore.exceptions.PrawcoreException) as e:
            print('PRAW exception ' + str(e))
            session = get_reddit("submissions_all", True)

        except Exception:
            import traceback; traceback.print_exc()

        # If a loop happens, sleep for a bit
        time.sleep(0.1)

def thread_comm(set_initial_comment, new_all_comm):
    """
    Watch comments and trigger comments events

    :param subreddit: subreddit to watch
    """

    while True:
        session = get_reddit("comments_all")
        # Get one submission and set it as the initial one
        logger.debug("Getting base comment")
        for comm in session.subreddit("all").stream.comments(pause_after=None, skip_existing=True):
            set_initial_comment(comm)
            break

        try:
            # Feed all comments
            for comm in session.subreddit("all").stream.comments(pause_after=None, skip_existing=True):
                new_all_comm(comm)

        except (praw.exceptions.PRAWException, prawcore.exceptions.PrawcoreException) as e:
            print('PRAW exception ' + str(e))
            session = get_reddit("comments_all", True)

        except Exception:
            import traceback; traceback.print_exc()

        # If a loop happens, sleep for a bit
        time.sleep(0.1)

def get_wiki(subreddit, wiki_name):
    return subreddit.wiki[wiki_name]

def edit_wiki(subreddit, wiki_name, content):
    subreddit.wiki[wiki_name].edit(content)

def tick(period, trigger):
    while True:
        # Sleep for the given period
        time.sleep(period)

        tnow = utcnow()
        try:
            trigger(tnow)
        except:
            import traceback; traceback.print_exc()