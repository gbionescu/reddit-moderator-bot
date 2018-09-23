from modbot import hook
from modbot import utils
from modbot.datastore import *
from urllib.parse import urlsplit
import logging
import subprocess
import configparser
logger = logging.getLogger("plugin")

SEC_IN_MIN = 60
MIN_IN_HOUR = 60

class subwrap():
    """Class that wraps a submission with custom things"""
    def __init__(self, sub):
        self.sub = sub
        self.warned = 0
        self.has_flair = False

class event():
    """Class representing an event - e.g. send message to an user"""
    def __init__(self, sub, time, mdata):
        self.sub = sub
        self.time = time
        self.mdata = mdata

class aflair():
    """Contains the conditions which decide whether flair filters match or not"""
    def cond_domain(self, arg, sub):
        logger.debug("Checking domain " + sub.domain + " for " + str(arg))

        # Check if any of the given domains match
        for elem in arg:
            if elem in sub.domain:
                logger.debug("Found as " + str(elem))
                return True

        return False

    def cond_title_contains(self, arg, sub):
        logger.debug("Checking title " + sub.title + " for " + str(arg))

        # Lower the title and check with substring in string
        title = sub.title.lower()
        for elem in arg:
            if elem in title:
                logger.debug("Found as " + str(elem))
                return True

        return False

    def cond_body_contains(self, arg, sub):
        # If it's not a self_post, it doesn't have a body and it's not a match
        if not sub.is_self:
            return False

        logger.debug("Checking body " + sub.selftext + " for " + str(arg))

        # Lower the body and check with substring in string
        body = sub.selftext.lower()
        for elem in arg:
            if elem in body:
                logger.debug("Found as " + str(elem))
                return True

        return False

    def __init__(self, sdict, name):
        self.priority = 1
        self.conditions = []
        self.name = name

        # Cycle through the keys and enqueue the conditions
        for key in sdict:
            arg_list = sdict[key].lower().split(",")

            if key == "domain":
                self.conditions.append((self.cond_domain, arg_list))

            elif key == "title_contains":
                self.conditions.append((self.cond_title_contains, arg_list))

            elif key == "body_contains":
                self.conditions.append((self.cond_body_contains, arg_list))

            elif key == "priority":
                self.priority = int(sdict[key])

            elif key == "flair_css_class":
                self.flair = sdict[key]

    def check(self, sub):
        logger.debug("Checking " + self.name)

        # Check all the conditions in the given order
        # If one returns False, then it's not a match
        for cond in self.conditions:
            result = cond[0](cond[1], sub)

            if result == False:
                return False

        return True

class submgr():
    """Class used for managing user notification events"""

    def __init__(self, warn_map, warn_msg, autoflair):
        self.slist = dslist("subs_list")
        self.wmap = warn_map
        self.sched = dslist("schedule_list")
        self.wmsg = warn_msg
        self.aflair = autoflair

    def add_sub(self, sub):
        # Only schedule notifications if it was not seen before
        if sub not in self.slist:
            self.slist.append(sub)
            self.sched_next_check(sub)

        # Clean up old submissions
        for sub in self.slist:
            if utils.utcnow() - sub.created_utc > 24 * SEC_IN_MIN * MIN_IN_HOUR:
                self.slist.remove(sub)

    def sched_next_check(self, sub):
        now = utils.utcnow()

        if now - sub.created_utc > 60:
            return

        start_marker = now
        sched_list = []

        for mark in self.wmap:
            check_time = start_marker + self.wmap[mark]

            sched_list.append(event(sub, check_time, mark))

        self.sched.extend(sched_list)
        logger.info("Added events for %s" % sub.permalink)

    def check_subs(self):
        now = utils.utcnow()
        # Loop through scheduled events
        for evt in self.sched:
            # If the gap between the scheduled time and current time is less
            # than 200s, trigger it. If it's older then something may have
            # happened
            if now >= evt.time and now - evt.time < 200:

                # Get the shorturl format
                short_url = "https://redd.it/" + evt.sub.id

                # Recheck the post for new flair or if it was deleted
                temp = reddit_inst.submission(url=short_url)
                self.sched.remove(evt)

                # TODO: make replacements nicely
                resolved_msg = self.wmsg
                resolved_msg = resolved_msg.replace("${SUBMISSION_LINK}", short_url)
                resolved_msg = resolved_msg.replace("${MESSAGE_NO}", str(evt.mdata))

                # TODO: if bot is moderator of sub, then check with .banned_by

                # Was if removed?
                if temp.is_crosspostable == False:
                    logger.info("Removed? " + short_url)
                    return

                # Did the author remove it?
                elif temp.author == None:
                    logger.info("Deleted? " + short_url)
                    return

                # Has the user updated the flair?
                if temp.link_flair_text is None and evt.mdata <= 3:
                    evt.sub.author.message("Flair post", resolved_msg)
                    logger.debug("Warning: %s, metadata %s" % (short_url, str(evt.mdata)))
                else:
                    logger.info("User flaired %s, after %d messages!" % (short_url, int(evt.mdata) - 1))

                    # Remove future checks for this submission
                    for fevt in self.sched:
                        if fevt.sub.id == evt.sub.id:
                            logger.debug("Removing future event for %s" % fevt.sub.id)
                            self.sched.remove(fevt)

                # Try adding auto flair
                if temp.link_flair_text is None and evt.mdata == 4:
                    proposed_flair = None

                    # Check each autoflair block until one returns True
                    for checker in self.aflair:
                        if checker.check(evt.sub) == True:
                            proposed_flair = checker.flair
                            break

                    # If there's a proposed flair, try adding it
                    if proposed_flair:
                        proposed_flair = proposed_flair

                        for choice in evt.sub.flair.choices():
                            if choice["flair_css_class"] == proposed_flair:
                                evt.sub.flair.select(choice["flair_template_id"])
                                break
            # If the event is too old, then just remove it
            elif now - evt.time > 12 * SEC_IN_MIN * MIN_IN_HOUR:
                self.sched.remove(evt)

reddit_inst = None      # Holds unique reddit instance
smgr = None             # submission manager instance
config_sub = None       # subreddit containing config data
debug_sub = None        # subreddit for debug
wiki_cfg = None         # parsed config data
wiki_content = None     # raw wiki content
old_wiki_content = ""   # old wiki content

@hook.periodic(first="5", period="5")
def check_events(bot, reddit):
    global smgr

    smgr.check_subs()

def update_wiki(bot, reddit):
    global smgr
    global wiki_content
    global old_wiki_content

    # Load the wiki page
    logger.info("Loading wiki config at " + utils.date())
    wiki_content = reddit.subreddit(config_sub).wiki['roautomoderator'].content_md

    if old_wiki_content != wiki_content:
        try:
            logger.info("Reconfiguring warn module")
            wiki_cfg = configparser.ConfigParser()
            wiki_cfg.read_string(wiki_content)

            autoflair_sections = []
            for section in wiki_cfg:
                if section.startswith("autoflair_"):
                    autoflair_sections.append(aflair(wiki_cfg[section], section))

            autoflair_sections = sorted(autoflair_sections, key=lambda prio: int(prio.priority))

            smgr = submgr(\
                    warn_map = {
                        1: int(wiki_cfg["NoFlairWarn"]["primul_warn_minute"]) * SEC_IN_MIN,
                        2: int(wiki_cfg["NoFlairWarn"]["al_doilea_warn_minute"]) * SEC_IN_MIN,
                        3: int(wiki_cfg["NoFlairWarn"]["al_treilea_warn_minute"]) * SEC_IN_MIN,
                        4: int(wiki_cfg["NoFlairWarn"]["autoflair_minute"]) * SEC_IN_MIN,
                    },
                    warn_msg = wiki_cfg["NoFlairWarn"]["mesaj"],
                    autoflair = autoflair_sections
                )
            old_wiki_content = wiki_content

            logger.info("Wiki page is ok")
        except:
            logger.info("Wiki error!")
            import traceback
            print(traceback.format_exc())

@hook.once()
def init_plugin(bot, reddit):
    global reddit_inst
    global config_sub
    global debug_sub

    reddit_inst = reddit
    config_sub = bot.config["config"]["config_sub"]
    debug_sub  = bot.config["config"]["debug_sub"]

    update_wiki(bot, reddit)

@hook.periodic(first="1", period="30")
def update_botlog(bot, reddit):
    update_wiki(bot, reddit)

    # Update log page
    subprocess.call(["rm out out1 || true"], shell=True)
    subprocess.call(['tail -1000 bot-out.log > out1'], shell=True)
    subprocess.call(['tac out1 > out'], shell=True)
    logdata = subprocess.check_output(["cat", "out"]).decode("utf-8")
    logdata = "    " + logdata.replace("\n", "\n    ")

    reddit.subreddit(debug_sub).wiki['roautomoderatorlog'].edit(logdata)

@hook.submission(subreddit='romania')
def call_new_sub(reddit, subreddit, submission):
    smgr.add_sub(submission)
