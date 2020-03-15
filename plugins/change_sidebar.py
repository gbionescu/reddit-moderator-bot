import ast
import random
import os
from collections import OrderedDict
from modbot import hook
from modbot.log import botlog
from modbot.utils import parse_wiki_content
from modbot.reddit_wrapper import get_subreddit
from modbot.utils_images import get_picture, gen_fname

plugin_documentation = """
Change sidebar pictures each day.

Configurable parameters are:

Example configuration:

"""
logger = botlog("change_sidebar")

# Store wiki configuration per subreddit
wiki_config = {}

START_MARKER = "[](/begin-pics)"
END_MARKER = "[](/end-pics)"


class PluginCfg():
    def __init__(self, config):
        self.items = OrderedDict()
        for item in config:
            self.items[item] = config[item]


def wiki_changed(sub, change):
    logger.debug("Wiki changed for change_sidebar, subreddit %s" % sub)
    cont = parse_wiki_content(change.content)

    if not cont:
        change.author.send_pm(
            "Error parsing the updated wiki page on %s" % sub)
        return
    else:
        if "Setup" in cont:
            wiki_config[sub.display_name] = PluginCfg(cont["Setup"])


wiki = hook.register_wiki_page(
    wiki_page="change_sidebar",
    description="Change sidebar pics",
    documentation=plugin_documentation,
    wiki_change_notifier=wiki_changed)


def select_picture(sub_name, cfg, storage):

    # Select the next item by index
    next_item = 0
    if sub_name in storage:
        next_item = storage[sub_name] + 1

    if next_item >= len(cfg.items.keys()):
        next_item = 0
    storage[sub_name] = next_item

    # Get name and link
    name = list(cfg.items.keys())[next_item]
    link = cfg.items[name]

    fname = gen_fname(sub_name, link)
    # Check if it exists, if not fetch it
    ok = None
    if not os.path.isfile(fname):
        ok = get_picture(cfg.items[name], fname)
    else:
        ok = True

    if ok:
        return name, fname
    else:
        return None, None


def set_sidebar_old_reddit(subreddit_name, choice, local_file):
    sub = get_subreddit(subreddit_name)

    # Get sidebar contents
    wiki = sub.wiki("config/sidebar")
    content = wiki.get_content()

    # Find the start/end markers in the sidebar
    start = content.find(START_MARKER)
    end = content.find(END_MARKER)

    if start == -1 or end == -1:
        logger.error("Could not find markers on %s" % subreddit_name)
        return

    # Upload the selected image as 'promsub'
    sub.stylesheet_upload_image("promsub", local_file)

    # Generate new sidebar content
    new_content = "%s\n%s\n\n%s" % (
        content[:start] + START_MARKER,
        "##### [%s](https://www.reddit.com/r/%s \"DailyLink\")" %
        (choice, choice),
        content[end:])

    # Update the sidebar
    wiki.edit(new_content)

    # Do a dummy sidebar edit (because reddit needs this apparently)
    sub.stylesheet_set_content(sub.stylesheet_get_content())
    logger.debug("Done on old reddit")


def set_sidebar_new_reddit(subreddit_name, choice, local_file):
    sub = get_subreddit(subreddit_name)
    pic_widget = None
    for widget in sub.get_sidebar_widgets():
        if widget.name == "DailyLink":
            pic_widget = widget
            break

    if not pic_widget:
        return

    pic_widget.set_image(local_file, "https://www.reddit.com/r/" + choice)
    logger.debug("Done on new reddit")


def set_sidebar(subreddit_name, cfg, storage):
    # Get the resources
    choice, local_file = select_picture(subreddit_name, cfg, storage)

    logger.debug("Setting sidebar to " + choice)

    if not choice or not local_file:
        return

    # Set old sidebar
    set_sidebar_old_reddit(subreddit_name, choice, local_file)

    # Set new sidebar
    set_sidebar_new_reddit(subreddit_name, choice, local_file)


@hook.periodic(cron="0 0 * * * *")
def do_change(storage):
    for sub_name, cfg in wiki_config.items():
        logger.debug("Changing sidebar on " + sub_name)
        set_sidebar(sub_name, cfg, storage)
