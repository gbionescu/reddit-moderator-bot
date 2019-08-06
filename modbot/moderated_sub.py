from modbot.log import botlog
from modbot.wiki_page import WatchedWiki
logger = botlog("plugin")

class ModeratedSubreddit():
    def __repr__(self):
        return self.subreddit.display_name

    def __init__(self, subreddit):
        self.subreddit = subreddit
        self.wiki_pages = {}
        self.crt_control_panel = ""

    def add_wiki(self, plugin):
        page = WatchedWiki(self.subreddit, plugin)
        if page.wiki_page not in self.wiki_pages:
            self.wiki_pages[page.wiki_page] = [page]
        else:
            if "w" in page.mode:
                for page in self.wiki_pages[page.wiki_page]:
                    if "w" in page.mode:
                        logger.debug("Page %s has already been configured by another plugin for %s. \
                            Initializing it in read only mode." % (page.wiki_page, self.subreddit.display_name))

                        self.wiki_pages[page.wiki_page].append(page)

    def get_wiki_list(self):
        return self.wiki_pages

    def get_wiki_values(self):
        for page in self.wiki_pages:
            for subpage in self.wiki_pages[page]:
                yield subpage

    def get_wiki_page(self, name):
        return self.wiki_pages[name]

    def get_control_panel(self):
        self.crt_control_panel = self.subreddit.wiki["control_panel"].content_md
        return self.crt_control_panel

    def set_control_panel(self, content):
        if self.crt_control_panel != content:
            logger.debug("Editing control panel for %s" % self)
            return self.subreddit.wiki["control_panel"].edit(content)

    def get_writable_wiki(self, wiki_page):
        for page in self.wiki_pages[wiki_page]:
            if "w" in page.mode:
                return page