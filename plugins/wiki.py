import configparser
from modbot import hook, utils
from modbot.moderated_sub import ModeratedSubreddit
from modbot.log import botlog
from modbot.hook import plugins_with_wikis

logger = botlog("wiki")

def parse_wiki_content(crt_content, parser="CFG_INI"):
    if parser == "CFG_INI":
        parser = configparser.ConfigParser(allow_no_value=True, strict=False)
        parser.read_string(crt_content)

        return parser

def prepare_wiki_content(content, indented=True):
    """
    Set wiki page content
    """
    if indented:
        lines = content.split("\n")
        content = "    ".join(i + "\n" for i in lines)

    return content

@hook.periodic(period=10)
def refresh_wikis(plugin_manager):
    """
    Refresh every wiki page and trigger update functions if needed
    """
    for sub in plugin_manager.moderated_subs.values():
        for wiki in sub.get_wiki_values():
            now = utils.utcnow()
            # Check if it's time to refresh
            if wiki.last_update + wiki.refresh_interval < now:
                wiki.last_update = now
                # If the content has changed, trigger the update function
                if wiki.update_content():
                    wiki.notifier(wiki.content)

def init_control_panel(plugin_manager):
    for sub in plugin_manager.moderated_subs.values():
        logger.debug("Configuring control panel for %s" % sub)

        if len(sub.get_wiki_list()) == 0:
            logger.debug("Skipping because there are no plugins available for this subreddit.")
            continue

        # Get current config page
        crt_content = parse_wiki_content(sub.get_control_panel())

        # Add header
        content = "###\n"
        content += "# A plugin can be enabled by adding it in the section below\n"
        content += "[Enabled Plugins]\n"

        # Add the existing enabled plugins
        if crt_content and "Enabled Plugins" in crt_content:
            for plugin in crt_content["Enabled Plugins"]:
                content += "%s\n" % plugin

        # Add footer
        content += "\n\n###### Available plugins for this subreddit"
        wiki_list = sub.get_wiki_list()
        for page in sorted(wiki_list.keys()):
            content += "\n\n### %s\n" % page
            content += "# %s\n" % sub.get_writable_wiki(page).description
            content += "# https://www.reddit.com/r/%s/wiki/%s" % (sub, page)

        sub.set_control_panel(prepare_wiki_content(content))

@hook.on_start
def create_wikis(plugin_manager):
    """
    Create wiki pages
    """

    for plugin in plugins_with_wikis:
        subreddits = plugin_manager.bot.get_moderated_subs()

        # If the wiki page is specific to a list of subreddits, then overwrite the variable
        if len(plugin.subreddits) != 0:
            subreddits = plugin.subreddits

        for sub in subreddits:
            # Skip user pages
            if sub.startswith("u_"):
                continue

            if sub not in plugin_manager.moderated_subs:
                plugin_manager.moderated_subs[sub] = ModeratedSubreddit(plugin_manager.get_subreddit(sub))

            logger.debug("Creating plugin %s for subreddit %s" % (plugin.wiki_page, sub))
            plugin_manager.moderated_subs[sub].add_wiki(plugin)

    init_control_panel(plugin_manager)