import logging
from modbot.log import botlog
from modbot.wiki_page import WatchedWiki
from modbot.hook import callback_type
logger = botlog("plugin")

class DispatchAll():
    # class CallbackCont():
    #     def __init__(self, lst):

    def __repr__(self):
        return "anything"

    def __init__(self, plugin_args):
        self.callbacks_peri = []
        self.callbacks_subs = []
        self.callbacks_coms = []
        self.callbacks_onstart = []
        self.callbacks = []

        self.wiki_pages_callbacks = {}

        self.plugin_args = plugin_args.copy()

    def call_plugin_func(self, element, args):
        """
        Call a plugin function

        :param element: plugin object containing information about what's to be called
        :param args: arguments that can be passed on to this function call
        """
        cargs = {}

        for farg in element.args:
            if farg in args.keys():
                cargs[farg] = args[farg]
            else:
                logger.error("Function %s requested %s, but it was not found in %s" % \
                     (element.func, farg, str(args.keys())))
                return

        try:
            element.func(**cargs)
        except Exception:
            logging.exception("Exception when running " + str(element.func))

    def add_plugin_arg(self, object, alias):
        """
        Register an object as a plugin argument
        """
        if alias not in self.plugin_args:
            self.plugin_args[alias] = object

    def run_on_start(self):
        for cbk in self.callbacks_onstart:
            self.call_plugin_func(cbk, self.plugin_args)

    def add_callback(self, func_list):
        # Check each callback type
        for cbk in func_list:
            # if cbk.ctype == callback_type.SUB:
            #     self.callbacks_subs.append(cbk)

            # elif cbk.ctype == callback_type.COM:
            #     self.callbacks_coms.append(cbk)

            # elif cbk.ctype == callback_type.PER:
            #     self.callbacks_peri.append(cbk)

            # elif cbk.ctype == callback_type.ONL:
            #     # If callback is of type on load, call it now
            #     self.call_plugin_func(cbk, self.plugin_args)
            # elif cbk.ctype == callback_type.ONS:
            #     self.callbacks_onstart.append(cbk)
            # else:
            #     logger.error("Unhandled function type: " + str(cbk.ctype))

            if cbk.wiki:
                if cbk.wiki.wiki_page not in self.wiki_pages_callbacks:
                    self.wiki_pages_callbacks[cbk.wiki.wiki_page] = []

                self.wiki_pages_callbacks[cbk.wiki.wiki_page].append(cbk)
                logger.debug("Adding it to wiki page: " + cbk.wiki.wiki_page + " on " + str(self))
            else:
                self.callbacks.append(cbk)
                logger.debug("Adding it to as generic to " + str(self))

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

class DispatchSubreddit(DispatchAll):
    def __repr__(self):
        return self.subreddit_name

    def __init__(self, subreddit, plugin_args):
        super().__init__(plugin_args)

        self.subreddit = subreddit
        self.subreddit_name = subreddit.display_name

        self.add_plugin_arg("subreddit", subreddit)

    def enable_moderated(self):
        self.mod = ModeratedSubreddit(self.subreddit)