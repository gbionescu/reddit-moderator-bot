import json
from flask import Flask

from modbot.utils import BotThread
from modbot.log import botlog
from modbot import reddit_wrapper as rw

logger = botlog("api")
app = Flask(__name__)

@app.route("/reddit/get_modqueue/<string:subreddit_name>")
def reddit_get_modqueue(subreddit_name):
    queue_items = list(rw.scrape_modqueue(subreddit_name))

    to_return = {}

    for item in queue_items:
        to_return[item.permalink] = item.item_type.user_reports

    return json.dumps(to_return)

def _start_server():
    app.run(host="127.0.0.1", port=32128, debug=False)

def start_server():
    logger.debug("Starting api server")
    BotThread(target=_start_server, name="api")
