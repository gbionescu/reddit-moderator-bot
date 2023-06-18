"""
Old style usernotes fetcher
"""
import base64
import json
import zlib

from modbot.reddit_wrapper import get_subreddit

def get_unotes(subreddit_name):
    subreddit = get_subreddit(subreddit_name)
    wiki_content = subreddit.wiki("usernotes").content

    try:
        unotes = json.loads(wiki_content)
    except Exception as e:
        raise Exception(f"Error reading json: {str(e)}")

    if unotes["ver"] != 6:
        raise Exception("Invalid usernotes version found, please upgrade")

    try:
        data_raw = zlib.decompress(base64.b64decode(unotes["blob"])).decode()
    except Exception as e:
        raise Exception(f"Error decoding json: {str(e)}")

    return unotes["constants"], json.loads(data_raw)
