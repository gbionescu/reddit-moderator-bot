import unicodedata
import string
from modbot import hook
from modbot.utils import timedata, utcnow
from modbot.utils_title import get_title

MIN_WORD_LEN = 3 # Skip words shorter than
MIN_WORDS_IN_TITLE = 5 # Skip titles shorter than
MAX_AGE = timedata.SEC_IN_DAY * 7 # Maximum age to keep posts
MIN_OVERLAP = 0.5 # Minumum overlap to report a post as repost
MAX_ACTION_TIME = timedata.SEC_IN_MIN # Maximum time to wait to take an action
EDITORIALIZE_OVERLAP = 0.9 # Overlap under which title editorialization is reported

def wiki_changed(sub, content):
    print("changed")

wiki = hook.register_wiki_page(
    wiki_page = "repost_detector",
    description = "Search for reposted articles and check for editorialized posts",
    documentation = "No configuration possible for now",
    wiki_change_notifier = wiki_changed)

def remove_accents(input_str):
    nfkd_form = unicodedata.normalize('NFKD', input_str)
    return u"".join([c for c in nfkd_form if not unicodedata.combining(c)])

def clean_title(title):
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

@hook.submission(wiki=wiki)
def new_post(submission, storage, reddit_inst):
    if "subs" not in storage:
        storage["subs"] = {}

    # Get current time
    tnow = utcnow()
    # Don't take action on old posts
    if tnow - submission.created_utc > MAX_ACTION_TIME:
        return

    no_shortw = clean_title(submission.title)
    if len(no_shortw) == 0:
        return

    # Check against old titles
    for post in storage["subs"].values():
        if post["shortlink"] == submission.shortlink:
            continue

        # Count how many words from the current title have been
        # found in the old title
        crt_found_words = 0
        for word in no_shortw:
            if word in post["filtered"]:
                crt_found_words += 1

        factor = crt_found_words / len(no_shortw)
        if factor > MIN_OVERLAP:
            post_sub = reddit_inst.submission(url=post["shortlink"])
            # Did the author remove it?
            if post_sub.author == None:
                continue
            # Was it removed?
            elif post_sub.is_crosspostable == False:
                continue

            submission.report("Possible repost of %s, with a factor of %f" % (post["shortlink"], factor))
            return

        # Check for a changed title
        if not submission.is_self:
            article_title = clean_title(get_title(submission.url))

            if len(article_title) == 0:
                return

            found_words = 0
            for word in article_title:
                if word in no_shortw:
                    found_words += 1

            factor = found_words / len(article_title)
            if factor < EDITORIALIZE_OVERLAP:
                submission.report("Possible editorialization with a factor of %f" % (factor))

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