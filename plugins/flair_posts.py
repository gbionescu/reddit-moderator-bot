import ast

from modbot import hook
from modbot.log import botlog
from modbot.wiki_page import parse_wiki_content
from modbot.utils import utcnow, timedata

plugin_documentation = """
This plugin can be configured to send messages to users that do not flair posts.
To configure the plugin, a section named [Setup] must be declared.
In the setup section you can define the 'message_intervals' variable which is a comma separated list of values which specify after how many minutes to send messages to users.
You can also define the 'message' variable, which defines how the message looks like. The message can contain the following variables:
SUBMISSION_LINK - link to the post
MESSAGE_NO - current message number
MAX_MESSAGES - the number of messages that will be sent.

If the user doesn't flair the post, you can set an autoflair interval, through the 'autoflair' variable.
Autoflairing is done depending on a set of rules that have the following format:
   [autoflair_foo]
   flair_css_class = "flair css class to set"
   title_contains = ["foo", "bar"]
   body_contains = ["foo", "bar"]
   domain = ["google.com", "amazon.com"]
   priority = 999

An autoflair rule is defined by adding a section that is prefixed by "autoflair_".
Each autoflair rule can contain one or multiple conditionals, that when satisfied, set the flair to the value set by 'flair_css_class'.
These conditionals can be:
- title_contains - list of words that should be in the title
- body_contains - if it's a self-post, then it checks if the self-post contains any of the given words
- domain - checks if the post is made from a specific domain
- priority - prioritizes condition checking. By default a rule has priority 0. Lower priority numbers, will make a rule be evaluated in the beginning.

See the example below for a complete configuration:

Example 1:

[Setup]
# Send a message every 5, 10, 20 and 25 minutes
message_intervals = 5, 10, 20, 25
# Try to autoflair after 30 minutes
autoflair = 30

message = Hi! Please flair ${SUBMISSION_LINK}. This is message number ${MESSAGE_NO} / ${MAX_MESSAGES}

[autoflair_questions]
title_contains = ["question", "wondering"]
flair_css_class = "question"

[autoflair_news1]
domain = ["cnn.com", "bloomberg.com"]
flair_css_class = "news"

[autoflair_news2]
body_contains = ["Macron", "Brexit"]
flair_css_class = "news"

***

Example 2:

[Setup]
# Send a message after 10 minutes
message_intervals = 10
# Try to autoflair after 1 minute
autoflair = 1

"""
logger = botlog("flair_posts")
MIN_GRANULARITY = timedata.SEC_IN_MIN

class AutoFlair():
    """
    Contains conditions which decide whether flair filters match or not
    """
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

        # Cycle through keys and enqueue the conditions
        for key in sdict:
            arg_list = ast.literal_eval(sdict[key].lower())

            if key == "domain":
                self.conditions.append((self.cond_domain, arg_list))

            elif key == "title_contains":
                self.conditions.append((self.cond_title_contains, arg_list))

            elif key == "body_contains":
                self.conditions.append((self.cond_body_contains, arg_list))

            elif key == "priority":
                self.priority = int(sdict[key])

            elif key == "flair_css_class":
                self.flair = arg_list

    def check(self, sub):
        logger.debug("Checking " + self.name)

        # Check all the conditions in the given order
        # If one returns False, then it's not a match
        for cond in self.conditions:
            result = cond[0](cond[1], sub)

            if result == False:
                return False

        return True

class Flair():
    """
    Store data about how autoflair is configured for a subreddit
    """
    def __init__(self, section):
        self.message_intervals = None
        self.autoflair = None
        self.message = None
        self.aflairs = []

        if "message_intervals" in section:
            self.message_intervals = sorted([int(i) for i in section["message_intervals"].split(",")])

        if "autoflair" in section:
            self.autoflair = int(section["autoflair"])

        if "message" in section:
            self.message = section["message"]

    def add_autoflair(self, section, name):
        self.aflairs.append(AutoFlair(section, name))

        # Sort by priority
        self.aflairs = sorted(self.aflairs, key=lambda prio: int(prio.priority))

    def get_lowest_time(self):
        """
        Get the lowest time limit for taking an action
        """

        cmp = []
        if self.message_intervals:
            cmp.append(self.message_intervals[0])

        if self.autoflair:
            cmp.append(self.autoflair)

        if len(cmp) > 0:
            return min(filter(lambda x: x is not None, cmp)) * timedata.SEC_IN_MIN
        else:
            return None

    def get_nb_levels(self):
        """
        Get number of notification levels
        """
        if len(self.message_intervals) > 0:
            return len(self.message_intervals)
        else:
            return 0

    def get_autoflair_int(self):
        return self.autoflair * timedata.SEC_IN_MIN

    def get_notif_time(self):
        for i in self.message_intervals:
            yield i * timedata.SEC_IN_MIN

# Store wiki configuration per subreddit
wiki_config = {}

def wiki_changed(sub, content):
    print("changed")
    cont = parse_wiki_content(content)

    # Section setup needed
    if "Setup" not in cont:
        return

    # Read the setup section
    cfg = Flair(cont["Setup"])

    # Read each autoflair section
    for section in cont:
        if section.startswith("autoflair_"):
            # Add it to config
            cfg.add_autoflair(cont[section], section)

    # Save the config
    wiki_config[sub] = cfg

# Register wiki page
wiki = hook.register_wiki_page(
    wiki_page="flair_posts",
    description="Ask users to flair posts",
    documentation=plugin_documentation,
    wiki_change_notifier=wiki_changed)

@hook.submission(wiki=wiki)
def submission(subreddit, submission, storage):
    if subreddit not in wiki_config:
        return

    tnow = utcnow()
    # If the post has been created more than the lowest time we can take an action
    lt = wiki_config[subreddit].get_lowest_time()
    if tnow - submission.created_utc > lt:
        # Skip the post
        return

    if "subs" not in storage:
        storage["subs"] = {}

    # Check for duplicates
    if submission.shortlink in storage["subs"]:
        return

    new = {}
    new["shortlink"] = submission.shortlink
    new["created_utc"] = submission.created_utc
    new["notif_level"] = 0
    new["max_level"] = wiki_config[subreddit].get_nb_levels()
    new["next_message"] = []
    new["link_flair_text"] = ""
    for interval in wiki_config[subreddit].get_notif_time():
        new["next_message"].append(submission.created_utc + interval)

    aflair = wiki_config[subreddit].get_autoflair_int()
    new["has_aflair"] = False
    if aflair:
        new["has_aflair"] = True
        new["aflair_time"] = submission.created_utc + aflair
        new["aflair_done"] = False

    storage["subs"][submission.shortlink] = new
    storage.sync()

def flair_updater(subreddit, storage, reddit_inst):
    if subreddit not in wiki_config:
        return

    to_remove = []
    for post in list(storage["subs"].values()):
        post_sub = reddit_inst.submission(url=post["shortlink"])

        # Did the author remove it?
        if post_sub.author == None:
            to_remove.append(post)
            continue
        # Was it removed?
        elif post_sub.is_crosspostable == False:
            to_remove.append(post)
            continue

        if post_sub.link_flair_text not in [None, ""]:
            post["link_flair_text"] = post_sub.link_flair_text
            storage.sync()

    # Clean up threads that are to be removed
    for post in to_remove:
        try:
            del storage["subs"][post["shortlink"]]
        except:
            pass
    if len(to_remove) > 0:
        storage.sync()

@hook.periodic(period=10, wiki=wiki)
def per(subreddit, storage, reddit_inst, send_pm, set_flair_id):
    if subreddit not in wiki_config:
        return

    if "subs" not in storage:
        return

    # Update the flairs first
    flair_updater(subreddit, storage, reddit_inst)

    tnow = utcnow()

    to_remove = []
    # Check each post
    for post in list(storage["subs"].values()):
        # If time has expired for the current notification level
        if post["max_level"] > post["notif_level"] and tnow - post["next_message"][post["notif_level"]] > 0:

            # If the difference between trigger time and present is larger than the minimum
            # granularity, then something may have happened (e.g. bot was stopped)
            if tnow - post["next_message"][post["notif_level"]] > MIN_GRANULARITY:
                to_remove.append(post)
                continue

            # Has the user updated the flair?
            if post["link_flair_text"] == "":
                post["notif_level"] += 1
                storage.sync()

                if post["notif_level"] > post["max_level"]:
                    raise ValueError()

                # Fill out a list of parameters to replace in the message
                args = {
                    "SUBMISSION_LINK": post["shortlink"],
                    "MESSAGE_NO": post["notif_level"],
                    "MAX_MESSAGES": post["max_level"]}

                # Replace magic words in message template
                msg = wiki_config[subreddit].message
                for k, v in args.items():
                    msg = msg.replace("${%s}" % k, str(v))

                crt_sub = reddit_inst.submission(url=post["shortlink"])
                send_pm(crt_sub.author, "Please flair your post", msg)
                logger.info("Sent message %d for %s" % (post["notif_level"], post["shortlink"]))
            else:
                to_remove.append(post)
                continue

        if post["has_aflair"] and not post["aflair_done"] and tnow - post["aflair_time"] > 0:
            post["aflair_done"] = True
            storage.sync()
            crt_sub = reddit_inst.submission(url=post["shortlink"])

            logger.info("Trying autoflair for %s" % post["shortlink"])
            proposed_flair = None

            # Check each autoflair block until one returns True
            for checker in wiki_config[subreddit].aflairs:
                if checker.check(crt_sub) == True:
                    proposed_flair = checker.flair
                    break

            # If there's a proposed flair, try adding it
            if proposed_flair:
                for choice in crt_sub.flair.choices():
                    if choice["flair_css_class"] == proposed_flair:
                        set_flair_id(crt_sub, choice["flair_template_id"])

        if post["max_level"] <= post["notif_level"]:
            if not post["has_aflair"] or (post["has_aflair"] and post["aflair_done"]):
                to_remove.append(post)
                continue

    # Clean up threads that are to be removed
    for post in to_remove:
        try:
            del storage["subs"][post["shortlink"]]
        except:
            pass
    if len(to_remove) > 0:
        storage.sync()
