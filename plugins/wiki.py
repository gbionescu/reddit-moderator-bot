
#
# This file creates wiki pages for each subreddit where a plugin is available.
# It also checks wiki pages for changes and notifies plugins
#

import argparse
import sys
from modbot import hook, utils
from modbot.utils import parse_wiki_content, prepare_wiki_content
from modbot.log import botlog
from modbot.hook import plugins_with_wikis
from modbot.reddit_wrapper import get_moderators_for_sub, get_bot_account_name

logger = botlog("wiki")


@hook.periodic(period=10)
def refresh_wikis(plugin_manager):
    """
    Refresh every wiki page and trigger update functions if needed
    """
    for sub in plugin_manager.get_moderated_subs():
        for wiki in plugin_manager.dispatchers[sub].get_wiki_values():
            now = utils.utcnow()
            # Check if it's time to refresh
            if wiki.last_update + wiki.refresh_interval < now:
                wiki.last_update = now
                # If the content has changed, trigger the update function
                if wiki.update_content() and wiki.notifier:
                    logger.debug("Wiki %s/%s changed" % (sub, wiki))
                    wiki.notifier(
                        plugin_manager.dispatchers[sub].subreddit, wiki.get_change_obj())


def init_control_panel(sub_name, plugin_list, sub_dispatcher):
    """
    Initialize the control panel for a subreddit
    """
    logger.debug("Configuring control panel for %s" % sub_dispatcher)

    # Get current config page
    crt_content = parse_wiki_content(sub_dispatcher.get_control_panel())
    logger.debug("Got control panel for %s" % sub_dispatcher)

    # Add header
    content = "###\n"
    content += "# A plugin can be enabled by adding it in the [Enabled Plugins] section.\n"
    content += "# After changing the control panel wiki, send a message to the bot through the following link:\n"
    content += "# https://www.reddit.com/message/compose?to={}&subject=ping&message=%2Fupdate_control_panel%20--subreddit%20{}\n".format(
        get_bot_account_name(), sub_name)
    content += "[Enabled Plugins]\n"

    if not crt_content:
        logger.error(
            "Could not get control panel for %s. Aborting update" % sub_name)
        return

    enabled_plugins = []
    # Add the existing enabled plugins
    if "Enabled Plugins" in crt_content:
        for plugin in crt_content["Enabled Plugins"]:
            content += "%s\n" % plugin
            logger.debug("[%s] Enabling plugin %s" % (sub_name, plugin))
            enabled_plugins.append(plugin)

    # Enable default enabled wikis
    for page in plugin_list:
        if page.default_enabled and page.wiki_page not in enabled_plugins:
            logger.debug("[%s] Enabling default plugin %s" %
                         (sub_name, page.wiki_page))
            enabled_plugins.append(page.wiki_page)
            content += "%s\n" % page.wiki_page

    # Add footer
    content += "\n\n###### Available plugins for this subreddit"
    for page in plugin_list:
        content += "\n\n### %s\n" % page.wiki_page
        content += "# %s\n" % page.description
        content += "# https://www.reddit.com/r/%s/wiki/%s\n" % (
            sub_dispatcher, page.wiki_page)

        if page.wiki_page in enabled_plugins:
            content += "# Current status: Enabled"
            # Only add it one time
            new_wiki = None
            if page.wiki_page not in sub_dispatcher.get_wiki_list():
                new_wiki = sub_dispatcher.add_wiki(page)
            sub_dispatcher.enable_wiki(page.wiki_page)

            # Call the wiki notifier with the current content
            if new_wiki and new_wiki.notifier:
                new_wiki.update_content()
                new_wiki.notifier(sub_dispatcher.subreddit,
                                  new_wiki.get_change_obj())
        else:
            content += "# Current status: Disabled"
            sub_dispatcher.disable_wiki(page.wiki_page)

    sub_dispatcher.set_control_panel(prepare_wiki_content(content))


def get_plugins_for_sub(sub):
    """
    Get what plugins are enabled/disabled for the given sub
    """
    plugins_for_crt_sub = []
    for plugin in plugins_with_wikis:
        # If the wiki page is specific to a list of subreddits
        # check if the current subreddit is one of them
        if plugin.subreddits and len(plugin.subreddits) != 0 and sub not in plugin.subreddits:
            continue

        plugins_for_crt_sub.append(plugin)

    plugins_for_crt_sub = sorted(
        plugins_for_crt_sub, key=lambda m: m.wiki_page)

    return plugins_for_crt_sub


@hook.on_start
def create_wikis(plugin_manager):
    """
    Create wiki pages
    """
    # Go through each moderated subreddit
    # TODO: handle situation where bot is invited to moderate after it's started
    for sub in plugin_manager.get_moderated_subs():
        # Skip user pages
        if sub.startswith("u_"):
            continue

        init_control_panel(
            sub_name=sub,
            plugin_list=get_plugins_for_sub(sub),
            sub_dispatcher=plugin_manager.dispatchers[sub])


@hook.command(permission=hook.permission.MOD)
def update_control_panel(message, cmd_args, plugin_manager):
    """
    Update the control panel for a subreddit
    """
    parser = argparse.ArgumentParser(prog='update_control_panel')
    parser.add_argument(
        "--subreddit", help="Subreddit that should have its control panel updated")
    args = parser.parse_args(cmd_args)

    # Check if the author moderates targeted sub
    if message.author.name not in get_moderators_for_sub(args.subreddit):
        message.author.send_pm(
            "You're not a moderator for that sub", "You can only post on moderated subreddits")
        return

    logger.info("Updating control panel for %s" % args.subreddit)

    init_control_panel(
        sub_name=args.subreddit,
        plugin_list=get_plugins_for_sub(args.subreddit),
        sub_dispatcher=plugin_manager.dispatchers[args.subreddit])
