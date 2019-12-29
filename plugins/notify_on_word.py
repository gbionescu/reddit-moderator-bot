import ast
from modbot import hook
from modbot.reddit_wrapper import get_subreddit
from modbot.log import botlog
from modbot.wiki_page import parse_wiki_content

plugin_documentation = """
Sends a modmail message when a specific word is detected in a comment or submission anywhere on reddit.
A word must be at least 4 letters long. Shorter expressions will be ignored.

Configurable parameters are:
- word_list - list of words or expressions to trigger messages on
- ignore_users - list of users to ignore

Example configuration:
[Setup]
word_list = ["bla bla", "asdfg", "123456"]
ignore_users = ["yosemitesam", "bugsbunny]
"""

MIN_LEN = 4
logger = botlog("notify_on_word")

# Store wiki configuration per subreddit
wiki_config = {}

class PluginCfg():
    def __init__(self, config):
        word_list = ast.literal_eval(config["word_list"])

        self.word_list = []
        for word in word_list:
            if len(word) <= MIN_LEN:
                continue
            self.word_list.append(word)

        self.ignore_users = ast.literal_eval(config["ignore_users"])

def wiki_changed(sub, change):
    logger.debug("Wiki changed for notify_on_word, subreddit %s" % sub)
    cont = parse_wiki_content(change.content)

    # Section setup needed
    if "Setup" not in cont:
        logger.debug("Wiki does not contain Setup. Exit")
        # If it's a recent edit, notify the author
        if change.recent_edit:
            change.author.send_pm("Error interpreting the updated wiki page on %s" % sub,
                "It does not contain the [Setup] section. Please read the documentation on how to configure it")
        return

    wiki_config[sub.display_name] = PluginCfg(cont["Setup"])

wiki = hook.register_wiki_page(
    wiki_page = "word_notifier",
    description = "Send modmail when a specified word is detected",
    documentation = plugin_documentation,
    wiki_change_notifier = wiki_changed)

def check_words(text, config, author):
    if author.name in config.ignore_users:
        return []

    found_words = []
    for word in config.word_list:
        if word in text:
            found_words.append(word)

    return found_words

@hook.submission()
def new_post(submission, reddit, subreddit):
    # Skip link posts
    if not submission.is_self:
        return

    for subreddit_name, config in wiki_config.items():
        word_list = check_words(submission.selftext, config, submission.author)

        if len(word_list) > 0:
            message_body = "Word list: %s\nLink: %s" % (str(word_list), submission.shortlink)
            get_subreddit(subreddit_name).send_modmail(
                "Given word/words has/have been found in a submission", message_body)

@hook.comment()
def new_comment(comment, reddit, subreddit):
    # Skip self posts
    for subreddit_name, config in wiki_config.items():
        word_list = check_words(comment.body, config, comment.author)

        if len(word_list) > 0:
            message_body = "Word list: %s\nLink: %s" % (str(word_list), comment.permalink)
            get_subreddit(subreddit_name).send_modmail(
                "Given word/words has/have been found in a comment", message_body)
