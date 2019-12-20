from modbot import hook
from modbot.log import botlog
from modbot.utils import timedata, utcnow
from modbot.wiki_page import parse_wiki_content
from modbot.utils_title import clean_title
from modbot.utils import calc_overlap_avg

plugin_documentation = """
This plugin checks if there are reposts by verifying if a newly submitted item
has a similar wording as a previous submission.

Configurable parameters are:
- minimum_word_length - the checker skips words shorter than set
- minimum_nb_words - the checker skips titles with a number of words less than set
- min_overlap_percent - how much the identified overlap should be percentage wise; valid values are between 0 and 100

The checker works like so:
1. When a new submission is posted it's processed
2. Words shorter than minimum_word_length are eliminated
3. If the title has a number of words less than minimum_nb_words, then it will not be processed any further
4. Else, it will look back at older submissions and compare titles:
5. For each older title it checks how many common words are between the two titles
6. If the percentage of common words relative to the title length is larger than min_overlap_percent it will get reported

Example configuration:
[Setup]
minimum_word_length = 2
minimum_nb_words = 3
min_overlap_percent = 50

A practical scenario for the example above would be:
- If the new title is "AAA BBB CC DDD EEE FF", it will be transformed into "AAA BBB DDD EEE"
- Assuming that there is an older submission with the title "EEE DDD BBB", the new submission will be reported because it has 3 common words with the old one

Recommended configuration:
[Setup]
minimum_word_length = 3
minimum_nb_words = 5
min_overlap_percent = 50
"""

MAX_AGE = timedata.SEC_IN_DAY * 7 # Maximum age to keep posts
MAX_ACTION_TIME = timedata.SEC_IN_MIN # Maximum time to wait to take an action

logger = botlog("repost_detector")

# Store wiki configuration per subreddit
wiki_config = {}

class RepostCfg():
    def __init__(self, config):
        self.min_overlap_percent = min(max(int(config["min_overlap_percent"]), 0), 100)
        self.minimum_nb_words = int(config["minimum_nb_words"])
        self.minimum_word_length = int(config["minimum_word_length"])

def wiki_changed(sub, change):
    logger.debug("Wiki changed for repost_detector, subreddit %s" % sub)
    cont = parse_wiki_content(change.content)

    # Section setup needed
    if "Setup" not in cont:
        logger.debug("Wiki does not contain Setup. Exit")
        # If it's a recent edit, notify the author
        if change.recent_edit:
            change.author.send_pm("Error interpreting the updated wiki page on %s" % sub,
                "It does not contain the [Setup] section. Please read the documentation on how to configure it")
        return

    wiki_config[sub.display_name] = RepostCfg(cont["Setup"])

wiki = hook.register_wiki_page(
    wiki_page = "repost_detector",
    description = "Search for reposted articles and check for editorialized posts",
    documentation = plugin_documentation,
    wiki_change_notifier = wiki_changed)

@hook.submission(wiki=wiki)
def new_post(submission, storage, reddit, subreddit):
    if "subs" not in storage:
        storage["subs"] = {}

    # Get wiki configuration
    if subreddit.display_name not in wiki_config:
        logger.debug("[%s] Not in wiki config %s" % (submission.shortlink, subreddit.display_name))
        return
    config = wiki_config[subreddit.display_name]

    logger.debug("[%s] New post submitted with title: %s" % (submission.shortlink, submission.title))

    # Get current time
    tnow = utcnow()

    # Don't take action on old posts
    if tnow - submission.created_utc > MAX_ACTION_TIME:
        logger.debug("[%s] Skipped because it's too old" % (submission.shortlink))
        return

    if submission.shortlink in storage["subs"]:
        logger.debug("[%s] Submission already added" % (submission.shortlink))
        return

    # Clean the title
    cleaned_title = clean_title(submission.title, config.minimum_word_length)

    if len(cleaned_title) >= config.minimum_nb_words:
        # Check against old titles
        for post in storage["subs"].values():
            # Calculate two-way overlap factor
            logger.debug("[%s] Checking\n\t%s\n\t%s" % (submission.shortlink, cleaned_title, post["filtered"]))

            overlap_factor = calc_overlap_avg(cleaned_title, post["filtered"])

            logger.debug("[%s] Calculated repost factor %f" % (submission.shortlink, overlap_factor))
            if overlap_factor > config.min_overlap_percent:
                post_sub = reddit.get_submission(url=post["shortlink"])
                # Did the author remove it?
                if post_sub.author == None:
                    continue
                # Was it removed?
                elif post_sub.is_crosspostable == False:
                    continue

                logger.debug("[%s] Reporting as dupe for %s / factor %f" %
                    (submission.shortlink, post["shortlink"], overlap_factor))
                submission.report("Possible repost of %s, with a factor of %f" % (post["shortlink"], overlap_factor))
                return
    else:
        logger.debug("[%s] Title is too short" % (submission.shortlink))
        return

    # Add new element
    new = {}
    new["original"] = submission.title
    new["filtered"] = cleaned_title
    new["shortlink"] = submission.shortlink
    new["created_utc"] = submission.created_utc

    # Eliminate old submissions
    for post in list(storage["subs"].values()):
        if tnow - post["created_utc"] > MAX_AGE:
            del storage["subs"][post["shortlink"]]

    storage["subs"][submission.shortlink] = new
    storage.sync()