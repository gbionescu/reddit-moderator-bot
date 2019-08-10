from modbot import hook

def wiki_changed(content):
    print("changed")

wiki = hook.register_wiki_page(
    wiki_page = "flair_posts",
    description = "Ask users to flair posts",
    wiki_change_notifier = wiki_changed
    )

@hook.submission(wiki=wiki)
def submission(submission):
    print(submission.subreddit.display_name)