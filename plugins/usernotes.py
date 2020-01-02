import json
import zlib
import base64

from modbot import hook
from modbot.reddit_wrapper import get_subreddit

@hook.report_command()
def get_notes(report):
    """
    Returns user notes for the reported item
    """

    subreddit = get_subreddit(report.subreddit_name)
    wiki_content = subreddit.wiki("usernotes").content

    unotes = json.loads(wiki_content)

    if unotes["ver"] != 6:
        report.author.send_pm("Usernotes decode error", "Invalid usernotes version found, please upgrade")
        return

    data_raw = zlib.decompress(base64.b64decode(unotes["blob"])).decode()
    data = json.loads(data_raw)

    if report.author_name not in data:
        report.author.send_pm("Usernotes not found", "No notes found")
        return

    reply = "User %s has the following notes:\n\n" % report.author_name
    for note in data[report.author_name]["ns"]:
        reply += note["n"] + "\n\n"

    report.author.send_pm("Usernotes", reply)
