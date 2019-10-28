import unicodedata
import string
from modbot import hook
from modbot.log import botlog
from modbot.utils import timedata, utcnow
from modbot.utils_title import get_title

MIN_WORD_LEN = 3 # Skip words shorter than
MIN_WORDS_IN_TITLE = 5 # Skip titles shorter than
MAX_AGE = timedata.SEC_IN_DAY * 7 # Maximum age to keep posts
MIN_OVERLAP = 0.5 # Minumum overlap to report a post as repost
MAX_OVERLAP = 1.0
MAX_ACTION_TIME = timedata.SEC_IN_MIN # Maximum time to wait to take an action
EDITORIALIZE_OVERLAP = 0.9 # Overlap under which title editorialization is reported
SKIP_EDITORIALIZE_DOMAIN = ["imgur.com", "facebook.com"]

logger = botlog("repost_detector")

def wiki_changed(sub, content):
    logger.debug("Wiki changed for repost_detector, subreddit %s" % sub)

wiki = hook.register_wiki_page(
    wiki_page = "repost_detector",
    description = "Search for reposted articles and check for editorialized posts",
    documentation = "No configuration possible for now",
    wiki_change_notifier = wiki_changed)

def remove_accents(input_str):
    nfkd_form = unicodedata.normalize('NFKD', input_str)
    return u"".join([c for c in nfkd_form if not unicodedata.combining(c)])

def clean_title(title):
    logger.debug("Cleaning title: %s" % title)
    if not title:
        return []

    # Remove punctuation, lower, remove accents and split
    split = remove_accents(
            title.translate(str.maketrans(dict.fromkeys(string.punctuation))).lower()
        ).split()

    # If title contains less than MIN_WORDS_IN_TITLE words, exit, too short
    if len(split) < MIN_WORDS_IN_TITLE:
        return []

    # Remove words shorter than MIN_WORD_LEN
    no_shortw = []
    for word in split:
        if len(word) <= MIN_WORD_LEN:
            continue

        no_shortw.append(word)

    return no_shortw

def calc_overlap(list1, list2):
    setdiff = set(list1).symmetric_difference(set(list2))

    return len(setdiff) / len(list1), len(setdiff) / len(list2)

@hook.submission(wiki=wiki)
def new_post(submission, storage, reddit_inst):
    if "subs" not in storage:
        storage["subs"] = {}

    logger.debug("[%s] New post submitted with title: %s" % (submission.shortlink, submission.title))

    # Get current time
    tnow = utcnow()
    # Don't take action on old posts
    if tnow - submission.created_utc > MAX_ACTION_TIME:
        logger.debug("[%s] Skipped because it's too old" % (submission.shortlink))
        return

    no_shortw = clean_title(submission.title)
    if len(no_shortw) == 0:
        logger.debug("[%s] Title is too short" % (submission.shortlink))
        return

    if submission.shortlink in storage["subs"]:
        logger.debug("[%s] Submission already added" % (submission.shortlink))
        return

    # Check against old titles
    for post in storage["subs"].values():
        # Calculate two-way overlap factor
        logger.debug("[%s] Checking\n\t%s\n\t%s" % (submission.shortlink, no_shortw, post["filtered"]))
        factor1, factor2 = calc_overlap(no_shortw, post["filtered"])

        logger.debug("[%s] Calculated repost factor %f/%f" % (submission.shortlink, factor1, factor2))
        if factor1 > MIN_OVERLAP and factor2 > MIN_OVERLAP and factor1 < MAX_OVERLAP and factor2 < MAX_OVERLAP:
            post_sub = reddit_inst.submission(url=post["shortlink"])
            # Did the author remove it?
            if post_sub.author == None:
                continue
            # Was it removed?
            elif post_sub.is_crosspostable == False:
                continue

            logger.debug("[%s] Reporting as dupe for %s / factor %f/%f" %
                (submission.shortlink, post["shortlink"], factor1, factor2))
            submission.report("Possible repost of %s, with a factor of %f/%f" % (post["shortlink"], factor1, factor2))
            return

    check_changed_title = True
    if not submission.is_self:
        for domain in SKIP_EDITORIALIZE_DOMAIN:
            if domain in submission.url:
                check_changed_title = False
                break
    else:
        check_changed_title = False

    # Check for a changed title
    if check_changed_title:
        article_title = clean_title(get_title(submission.url))

        if len(article_title) == 0:
            logger.debug("[%s] No title, could not check article" % (submission.shortlink))
            return

        logger.debug("[%s] Checking for editorialization\n\t%s\n\t%s" % (submission.shortlink, article_title, no_shortw))

        factor1, factor2 = calc_overlap(article_title, no_shortw)
        logger.debug("[%s] Calculated editorialized factor %f/%f" % (submission.shortlink, factor1, factor2))

        if factor1 < EDITORIALIZE_OVERLAP and factor2 < EDITORIALIZE_OVERLAP:
            logger.debug("[%s] Reporting as editorialized" % submission.shortlink)
            submission.report("Possible editorialization with a factor of %f/%f" % (factor1, factor2))

    # Add new element
    new = {}
    new["original"] = submission.title
    new["filtered"] = no_shortw
    new["shortlink"] = submission.shortlink
    new["created_utc"] = submission.created_utc

    for post in storage["subs"].values():
        if tnow - post["created_utc"] > MAX_AGE:
            del storage["subs"][post["shortlink"]]

    storage["subs"][submission.shortlink] = new
    storage.sync()