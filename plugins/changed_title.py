import ast
from modbot import hook
from modbot.log import botlog
from modbot.utils import timedata, utcnow
from modbot.utils import calc_overlap_avg, parse_wiki_content
from modbot.utils_title import get_title, clean_title

plugin_documentation = """
This plugin checks if a link post has been posted with a different title than the original one.
If the difference is larger than a given limit, the post is reported.

Configurable parameters are:
- minimum_overlap_percent - the post title and the article title must overlap at least the given amount, else it's reported (value should be given between 0 and 100)
- domains - list of domains that should be checked
- ignore_users - list of users to ignore

Example configuration:
minimum_overlap_percent = 60
domains = ["google.com", "blabla.co.uk"]
ignore_users = ["AutoModerator"]
"""

MAX_ACTION_TIME = timedata.SEC_IN_MIN # Maximum time to wait to take an action
logger = botlog("changed_title")

# Store wiki configuration per subreddit
wiki_config = {}

class PluginCfg():
    def __init__(self, config):
        self.domains = []
        self.ignore_users = []
        # Mark that a configuration is valid
        self.valid = False

        if "minimum_overlap_percent" not in config:
            return

        self.minimum_overlap_percent = min(max(int(config["minimum_overlap_percent"]), 0), 100)

        if "domains" in config:
            self.domains = ast.literal_eval(config["domains"])

        if "ignore_users" in config:
            raw_users = ast.literal_eval(config["ignore_users"])

            for user in raw_users:
                self.ignore_users.append(user.lower())

        self.valid = True

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

    wiki_config[sub.display_name] = PluginCfg(cont["Setup"])

wiki = hook.register_wiki_page(
    wiki_page = "changed_title",
    description = "Check for posts that have titles different than the articles",
    documentation = plugin_documentation,
    wiki_change_notifier = wiki_changed)

@hook.submission(wiki=wiki)
def new_post(submission, reddit, subreddit):
    # Skip self posts
    if submission.is_self:
        return

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

    # Check if the domain is in the configured list
    domain_valid = False
    for domain in config.domains:
        if not submission.url:
            break
        if domain in submission.url:
            domain_valid = True
            break

    if not domain_valid:
        return

    # Check if the user should be ignored
    if submission.author.name.lower() in config.ignore_users:
        return

    # Get the title and clean it
    article_title = clean_title(get_title(submission.url))
    if len(article_title) == 0:
        return

    # Clean the submission title too
    submission_title = clean_title(submission.title)
    if len(submission_title) == 0:
        return

    logger.debug("[%s] Checking for editorialization\n\t%s\n\t%s" % (submission.shortlink, article_title, submission_title))

    overlap_factor = calc_overlap_avg(article_title, submission_title)

    logger.debug("[%s] Calculated editorialized factor %f" % (submission.shortlink, overlap_factor))

    # If there is too little overlap, report it
    if overlap_factor < config.minimum_overlap_percent:
        submission.report("Possible editorialization with a factor of %.2f%%" % (overlap_factor))