# from modbot import hook

# def wiki_changed(content):
#     print("changed")

# hook.register_wiki_page(
#     wiki_page = "control_panel",
#     description = "Wiki page where plugins can be configured",
#     wiki_change_notifier = wiki_changed
#     )

# @hook.on_start
# def init_control_panel(bot):
#     # Get list of distinct subreddits
#     distinct_subs = []
#     for sub_page in bot.watched_wikis.keys():
#         sub = sub_page.split("@")[0]
#         if sub not in distinct_subs:
#             distinct_subs.append(sub)

#     for sub in distinct_subs:
#         # Get current config page
#         crt_content = bot.get_parsed_wiki_content(sub, "control_panel")

#         # Add header
#         content = "###\n"
#         content += "# A plugin can be enabled by adding it in the section below\n"
#         content += "[Enabled Plugins]\n"

#         # Add the existing enabled plugins
#         if crt_content and "Enabled Plugins" in crt_content:
#             for plugin in crt_content["Enabled Plugins"]:
#                 content += "%s\n" % plugin

#         # Add footer
#         content += "\n\n###### Available plugins for this subreddit"
#         plugin_list = []
#         for page in bot.watched_wikis.keys():
#             if page.split("@")[0] == sub:
#                 plugin_list.append(page.split("@")[1])

#         for page in sorted(set(plugin_list)):
#             content += "\n\n### %s\n" % bot.watched_wikis["%s@%s" % (sub, page)].wiki_page
#             content += "# %s\n" % bot.watched_wikis["%s@%s" % (sub, page)].description
#             content += "# https://www.reddit.com/r/%s/wiki/%s" % (sub, page)

#         bot.set_wiki_content(sub, "control_panel", content)