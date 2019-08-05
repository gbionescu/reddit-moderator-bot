from modbot import hook

def wiki_changed():
    print("changed")

hook.register_wiki_page(
    wiki_page = "repost_detector",
    description = "Search for reposted articles",
    wiki_change_notifier = wiki_changed,
    subreddits=["RoAutoModerator"])
