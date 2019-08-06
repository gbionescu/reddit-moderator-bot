import prawcore
from modbot import utils
from modbot.log import botlog

logger = botlog("wiki_page")
EMPTY_WIKI = ""

class WatchedWiki():
    def __init__(self, subreddit, plugin):
        self.sub = subreddit
        self.subreddit_name = subreddit.display_name
        self.plugin = plugin

        self.content = ""
        try:
            self.content = self.sub.wiki[self.plugin.wiki_page].content_md
        except prawcore.exceptions.NotFound:
            logger.debug("Subreddit %s does not contain wiki %s. Creating it." %
                    (subreddit.display_name, self.plugin.wiki_page))
            self.sub.wiki[self.plugin.wiki_page].edit(EMPTY_WIKI)
            self.content = EMPTY_WIKI

        self.old_content = self.content
        self.last_update = utils.utcnow()
        self.refresh_interval = self.plugin.refresh_interval
        self.notifier = self.plugin.wiki_change_notifier
        self.wiki_page = self.plugin.wiki_page
        self.description = self.plugin.description

        # Initialize wiki r/w
        self.mode = ""
        if "r" in plugin.mode:
            self.mode += "r"

        if "w" in plugin.mode:
            self.mode += "w"

    def update_content(self):
        """
        Update page content and return True if changed, False otherwise
        """
        changed = False
        self.content = self.sub.wiki[self.plugin.wiki_page].content_md

        if self.content != self.old_content:
            changed = True

        self.old_content = self.content
        self.last_update = utils.utcnow()

        return changed

    def set_content(self, content):
        if "w" in self.mode:
            self.sub.wiki[self.plugin.wiki_page].edit(content)