from modbot import hook
from modbot import utils
from modbot.log import botlog

start_date = utils.date()
logger = botlog("audit")

wiki = hook.register_wiki_page(
    wiki_page = "bot_startup",
    description = "Marks when the bot has started up (always enabled)",
    default_enabled=True,
    subreddits=[hook.subreddit_type.MASTER_SUBREDDIT])

@hook.on_start(wiki=wiki)
def mark_startup(wiki_pages):
    page = wiki_pages["bot_startup"][0]
    page.update_content()

    new_content = page.content.split("\n")
    new_content.insert(0, "Bot startup: %s; Plugin startup: %s\n" % (start_date, utils.date()))
    logger.info("Bot startup: %s; Plugin startup: %s\n" % (start_date, utils.date()))

    # Only upload the last 1000 startups
    page.set_content("\n".join(new_content[:1000]))

