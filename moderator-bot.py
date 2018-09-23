import praw
import os
import threading
import configparser
from modbot.plugin import plugin_manager

USER_AGENT="Romania moderator bot by /u/programatorulupeste"
reddit = praw.Reddit("ro_moderator_bot", user_agent=USER_AGENT)

# Load configs
config = configparser.ConfigParser()
config.read("reddit-bot.ini")

# Check if the config wants us to enable plugin reloading
with_reload = False
if "debug" in config and "reload" in config["debug"]:
    with_reload = True

# Parse the subreddit list to watch
subreddits = config["config"]["watch_subs"].split(",")
subreddits = map(str.strip, subreddits)

# Load plugins
pmgr = plugin_manager([os.path.abspath("plugins")], reddit, with_reload, config)
pmgr.watch_subs(subreddits)

while True:
    import time
    time.sleep(1)
