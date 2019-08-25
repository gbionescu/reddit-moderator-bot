
import sys
from modbot import hook, utils
from modbot.wiki_page import parse_wiki_content, prepare_wiki_content
from modbot.log import botlog
from modbot.hook import plugins_with_wikis

logger = botlog("wiki")

@hook.periodic(period=10)
def refresh_wikis(plugin_manager):
    """
    Refresh every wiki page and trigger update functions if needed
    """
    for sub in plugin_manager.bot.get_moderated_subs():
        for wiki in plugin_manager.dispatchers[sub].get_wiki_values():
            now = utils.utcnow()
            # Check if it's time to refresh
            if wiki.last_update + wiki.refresh_interval < now:
                wiki.last_update = now
                # If the content has changed, trigger the update function
                if wiki.update_content():
                    wiki.notifier(wiki.content)

def init_control_panel(sub_name, plugin_list, plugin_manager):
    sub = plugin_manager.dispatchers[sub_name]
    logger.debug("Configuring control panel for %s" % sub)

    # Get current config page
    crt_content = parse_wiki_content(sub.get_control_panel())

    # Add header
    content = "###\n"
    content += "# A plugin can be enabled by adding it in the section below\n"
    content += "[Enabled Plugins]\n"

    enabled_plugins = []
    # Add the existing enabled plugins
    if crt_content and "Enabled Plugins" in crt_content:
        for plugin in crt_content["Enabled Plugins"]:
            content += "%s\n" % plugin

            enabled_plugins.append(plugin)

    # Enable default enabled wikis
    for page in plugin_list:
        if page.default_enabled and page.wiki_page not in enabled_plugins:
            enabled_plugins.append(page.wiki_page)
            content += "%s\n" % page.wiki_page

    # Add footer
    content += "\n\n###### Available plugins for this subreddit"
    for page in plugin_list:
        content += "\n\n### %s\n" % page.wiki_page
        content += "# %s\n" % page.description
        content += "# https://www.reddit.com/r/%s/wiki/%s\n" % (sub, page.wiki_page)

        if page.wiki_page in enabled_plugins:
            content += "# Current status: Enabled"
            # Only add it one time
            if page.wiki_page not in sub.get_wiki_list():
                sub.add_wiki(page)
            sub.enable_wiki(page.wiki_page)
        else:
            content += "# Current status: Disabled"
            sub.disable_wiki(page.wiki_page)

    sub.set_control_panel(prepare_wiki_content(content))

@hook.on_start
def create_wikis(plugin_manager):
    """
    Create wiki pages
    """

    # Go through each moderated subreddit
    # TODO: handle situation where bot is invited to moderate after it's started
    for sub in plugin_manager.bot.get_moderated_subs():
        # Skip user pages
        if sub.startswith("u_"):
            continue

        plugins_for_crt_sub = []
        for plugin in plugins_with_wikis:
            # If the wiki page is specific to a list of subreddits
            # check if the current subreddit is one of them
            if plugin.subreddits and len(plugin.subreddits) != 0 and sub not in plugin.subreddits:
                continue

            if sub not in plugin_manager.dispatchers:
                logger.error("%s not in dispatcher list" % sub)
                sys.exit(0)

            plugins_for_crt_sub.append(plugin)

        plugins_for_crt_sub = sorted(plugins_for_crt_sub, key=lambda m: m.wiki_page)

        init_control_panel(sub, plugins_for_crt_sub, plugin_manager)

@hook.periodic(period=30)
def refresh_control_panels(plugin_manager):
    create_wikis(plugin_manager)