from modbot import hook

def wiki_changed():
    print("changed")

hook.register_wiki_page(
    wiki_page = "control_panel",
    description = "Wiki page where plugins can be configured",
    wiki_change_notifier = wiki_changed
    )

@hook.on_start
def init_control_panel(bot):
    for sub in bot.watched_wikis:
        # Get current config page
        crt_content = bot.get_parsed_wiki_content(sub, "control_panel")

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
        for page in bot.watched_wikis[sub]:
            content += "\n\n### %s\n" % bot.watched_wikis[sub][page].plugin.wiki_page
            content += "# %s\n" % bot.watched_wikis[sub][page].plugin.description
            content += "# https://www.reddit.com/r/%s/wiki/%s" % (sub, page)

        bot.set_wiki_content(sub, "control_panel", content)