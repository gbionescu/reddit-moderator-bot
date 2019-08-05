from modbot import hook

def wiki_changed():
    print("changed")

hook.register_wiki_page(
    wiki_page = "flair_posts",
    description = "Ask users to flair posts",
    wiki_change_notifier = wiki_changed
    )