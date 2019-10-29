import prawcore
import configparser
from modbot import utils
from modbot.log import botlog
from modbot.storage import dsdict

logger = botlog("wiki_page")
EMPTY_WIKI = ""

class WatchedWiki():
    DOC_BEGIN = "    ###### <Documentation> (do not edit below)\n\n"
    DOC_END = "\n\n    ###### <Documentation> (do not edit above)\n"
    def __init__(self, subreddit, plugin):
        self.sub = subreddit
        self.subreddit_name = subreddit.display_name
        self.plugin = plugin

        self.content = ""
        try:
            self.content = self.sub.wiki(self.plugin.wiki_page).get_content()
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
        self.raw_documentation = self.plugin.documentation
        self.documentation = None

        # Provide extra args for upper classes
        self.args = {}

        # Create location for small storage
        self.storage = dsdict(self.subreddit_name, self.wiki_page)
        self.args["storage"] = self.storage

        # Initialize wiki r/w
        self.mode = ""
        if "r" in plugin.mode:
            self.mode += "r"

        if "w" in plugin.mode:
            self.mode += "w"

        # Pre generate documentation string
        if self.raw_documentation:
            self.documentation = WatchedWiki.DOC_BEGIN
            split_doc = self.raw_documentation.strip().split("\n")

            self.documentation += "\n".join(("    ## " + line).rstrip() for line in split_doc)
            self.documentation += WatchedWiki.DOC_END

        # Set documentation if not already present
        self.content = self.content.replace("\r", "")
        if self.documentation and self.documentation.strip() not in self.content:
            begin = self.content.replace("\r", "").find(WatchedWiki.DOC_BEGIN)
            end = self.content.replace("\r", "").find(WatchedWiki.DOC_END)

            if begin != -1 and end != -1:
                self.content = self.content[0:begin] + self.documentation + self.content[end + len(WatchedWiki.DOC_END):]
            else:
                self.content = self.documentation + self.content

            self.set_content(self.content, with_documentation=False)

    def update_content(self):
        """
        Update page content and return True if changed, False otherwise
        """
        changed = False
        self.content = self.sub.wiki(self.plugin.wiki_page).get_content()

        if self.content != self.old_content:
            changed = True

        self.old_content = self.content
        self.last_update = utils.utcnow()

        return changed

    def set_content(self, content, with_documentation=True):
        """
        Set wiki page content
        """
        if "w" in self.mode:
            if self.documentation and with_documentation:
                content = self.documentation + content

            self.sub.wiki(self.plugin.wiki_page).edit(content)
        else:
            logger.debug("Can't write to %s, because it's read only" % self.plugin.wiki_page)

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