from discord_webhook import DiscordWebhook
from modbot import hook
from modbot.log import botlog
from modbot.wiki_page import parse_wiki_content

plugin_documentation = """
The plugin sends submissions or modlog items to given discord webhooks.

Configurable parameters are:
- modlog - sends modlog items to the webhook
- submissions - sends new submissions to the webhook

Example configuration:
modlog = http://webhook1
submissions = http://webhook2
"""
logger = botlog("webhook_plugin")

# Store wiki configuration per subreddit
wiki_config = {}

class PluginCfg():
    def __init__(self, config):
        if "modlog" in config:
            self.modlog = config["modlog"]

        if "submissions" in config:
            self.submissions = config["submissions"]

def wiki_changed(sub, change):
    logger.debug("Wiki changed for repost_detector, subreddit %s" % sub)
    cont = parse_wiki_content(change.content)

    if not cont:
        change.author.send_pm("Error parsing the updated wiki page on %s" % sub)
        return

    try:
        wiki_config[sub.display_name] = PluginCfg(cont["Setup"])
    except:
        pass

wiki = hook.register_wiki_page(
    wiki_page = "webhook_streamer",
    description = "Stream items to webhooks",
    documentation = plugin_documentation,
    wiki_change_notifier = wiki_changed)

@hook.submission(wiki=wiki)
def new_post(submission, subreddit_name):
    # If the subreddit was configured
    if subreddit_name not in wiki_config:
        return

    stype = None
    if submission.is_self:
        stype = "**Self post**"
    else:
        stype = "**Link post**"

    text = "%s: %s by %s <%s>" % (stype, submission.title, submission.author.name, submission.shortlink)
    webhook = DiscordWebhook(wiki_config[subreddit_name].submissions, content=text)
    webhook.execute()

def send_modlog(item, url):
    text = ""

    if not item.target_author:
        text = "`[%s][%s] %s` " % (item.mod.name, item.action, item.details)
    else:
        text = "`[%s][%s][%s] %s` " % (item.mod_name, item.action, item.target_author, item.details)

    if item.description:
        text += "`%s`" % item.description

    if item.target_permalink:
        text += "<https://reddit.com" + item.target_permalink + ">"

    webhook = DiscordWebhook(url, content=text)
    webhook.execute()

@hook.modlog(wiki=wiki)
def new_modlog_item(modlog, subreddit_name):
    # If the subreddit was configured
    if subreddit_name in wiki_config:
        send_modlog(modlog, wiki_config[subreddit_name].modlog)
