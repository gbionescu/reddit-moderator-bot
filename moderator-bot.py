import praw
import os
import threading
from modbot.plugin import plugin_manager

threads = []
subreddits = ['romania']

USER_AGENT="Romania moderator bot by /u/programatorulupeste"
reddit = praw.Reddit("ro_moderator_bot", user_agent=USER_AGENT)

# Load plugins
pmgr = plugin_manager([os.path.abspath("plugins")], reddit)
pmgr.watch_subs(subreddits)

while True:
    import time
    time.sleep(1)
