import logging
import threading
import copy
from modbot import utils
from modbot.log import botlog
from modbot.wiki_page import WatchedWiki
from modbot.hook import callback_type
logger = botlog("mod_sub")

class DispatchAll():
    class HookContainer():
        def __init__(self, to_call):
            self.callbacks_peri = []
            self.callbacks_subs = []
            self.callbacks_coms = []
            self.callbacks_onstart = []
            self.callbacks = []
            self.to_call = to_call

        def add_hook(self, func, last_exec=utils.utcnow()):
            # Create an unique copy for this container
            func = copy.copy(func)
            if func.ctype == callback_type.SUB:
                self.callbacks_subs.append(func)

            elif func.ctype == callback_type.COM:
                self.callbacks_coms.append(func)

            elif func.ctype == callback_type.PER:
                self.callbacks_peri.append(func)
                if func.last_exec == 0:
                    func.set_last_exec(last_exec)

            elif func.ctype == callback_type.ONL:
                # If callback is of type on load, call it now
                self.to_call(func)
            elif func.ctype == callback_type.ONS:
                self.callbacks_onstart.append(func)
            else:
                logger.error("Unhandled function type: " + str(func.ctype))

        def run_on_start(self, with_thread=False):
            for cbk in self.callbacks_onstart:
                self.to_call(cbk, with_thread)

        def merge_container(self, cont):
            # Merge periodic callbacks
            self.callbacks_peri.extend(cont.callbacks_peri)

            # Merge submissions
            self.callbacks_subs.extend(cont.callbacks_subs)

            # Merge comments
            self.callbacks_coms.extend(cont.callbacks_coms)

            # Merge on start
            self.callbacks_onstart.extend(cont.callbacks_onstart)

            self.callbacks.extend(cont.callbacks)

        def run_periodic(self, start_time, tnow):
            # Go through periodic list
            for el in self.callbacks_peri:
                # Trigger it at the 'first' interval initially
                if el.first:
                    if start_time + int(el.first) < tnow:
                        el.set_last_exec(tnow)
                        self.to_call(el, True)

                        # Delete the attribute so that it's not triggered again
                        el.first = None

                elif el.period:
                    # Check if 'period' has passed since last executed
                    if el.last_exec + int(el.period) < tnow:
                        el.set_last_exec(tnow)
                        self.to_call(el, True)

        def run_submission(self, submission):
            for cbk in self.callbacks_subs:
                self.to_call(cbk, False, {"submission": submission})

        def run_comment(self, comment):
            for cbk in self.callbacks_coms:
                self.to_call(cbk, False, {"comment": comment})

    def __repr__(self):
        return "generic"

    def __init__(self, plugin_args):
        self.generic_hooks = self.HookContainer(self.call_plugin_func)
        self.enabled_wiki_hooks = self.HookContainer(self.call_plugin_func)
        self.enabled_wikis = []

        self.wiki_pages_callbacks = {}

        self.plugin_args = plugin_args.copy()

        self.logger = botlog(self.__repr__())

    def call_plugin_func(self, el, with_thread, extra_args={}):
        """
        Call a plugin function

        :param element: plugin object containing information about what's to be called
        :param args: arguments that can be passed on to this function call
        """
        def trigger_func(element, args):
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
        if with_thread:
            self.logger.debug("triggering " + str(el.func))
            pthread = threading.Thread(
                name="periodic_" + str(el.func),
                target = trigger_func,
                args=(el, {**self.plugin_args, **extra_args},))

            pthread.setDaemon(True)
            pthread.start()
        else:
            trigger_func(el, {**self.plugin_args, **extra_args})

    def add_plugin_arg(self, object, alias):
        """
        Register an object as a plugin argument
        """
        if alias not in self.plugin_args:
            self.plugin_args[alias] = object

    def add_callback(self, func_list):
        # Check each callback type
        for cbk in func_list:
            if cbk.wiki:
                if cbk.wiki.wiki_page not in self.wiki_pages_callbacks:
                    self.wiki_pages_callbacks[cbk.wiki.wiki_page] = self.HookContainer(self.call_plugin_func)

                self.wiki_pages_callbacks[cbk.wiki.wiki_page].add_hook(cbk)
                self.logger.debug("Adding it to wiki page: " + cbk.wiki.wiki_page + " on " + str(self))
            else:
                self.generic_hooks.add_hook(cbk)
                self.logger.debug("Adding it to as generic to " + str(self))

    def rebuild_wiki_hooks(self):
        # Create the container each time
        self.enabled_wiki_hooks = self.HookContainer(self.call_plugin_func)
        for wiki in self.enabled_wikis:
            # Call on start hooks for the current wiki
            self.wiki_pages_callbacks[wiki].run_on_start()
            # Add it to the enabled wiki hook list
            self.enabled_wiki_hooks.merge_container(self.wiki_pages_callbacks[wiki])

    def enable_wiki(self, wiki):
        if wiki not in self.enabled_wikis:
            self.logger.debug("Enabling wiki %s for %s" % (wiki, self))
            self.enabled_wikis.append(wiki)

            self.rebuild_wiki_hooks()

    def disable_wiki(self, wiki):
        if wiki in self.enabled_wikis:
            self.logger.debug("Disabling wiki %s" % (wiki))
            self.enabled_wikis.remove(wiki)

            self.rebuild_wiki_hooks()

    def run_on_start(self, with_thread=False):
        self.logger.debug("Running on start for generic hooks")
        self.generic_hooks.run_on_start(with_thread)
        self.logger.debug("Running on start for wiki hooks")
        self.enabled_wiki_hooks.run_on_start(with_thread)

    def run_periodic(self, start_time, timestamp):
        self.generic_hooks.run_periodic(start_time, timestamp)
        self.enabled_wiki_hooks.run_periodic(start_time, timestamp)

    def run_submission(self, submission):
        self.generic_hooks.run_submission(submission)
        self.enabled_wiki_hooks.run_submission(submission)

    def run_comment(self, comment):
        self.generic_hooks.run_comment(comment)
        self.enabled_wiki_hooks.run_comment(comment)

class DispatchSubreddit(DispatchAll):
    def __repr__(self):
        return self.subreddit.display_name

    def __init__(self, subreddit, plugin_args):
        self.subreddit = subreddit
        self.wiki_pages = {}
        self.crt_control_panel = ""
        super().__init__(plugin_args)

        self.add_plugin_arg(subreddit, "subreddit")


    def add_wiki(self, plugin):
        """
        Add a wiki page to the current subreddit.
        """
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
        """
        Get a dictionary of wiki pages that are enabled for the current subreddit
        """
        return self.wiki_pages

    def get_wiki_values(self):
        for page in self.wiki_pages:
            for subpage in self.wiki_pages[page]:
                yield subpage

    def get_wiki_page(self, name):
        """
        Get a specific wiki page
        """
        return self.wiki_pages[name]

    def get_control_panel(self):
        """
        Get the control panel content
        """
        self.crt_control_panel = self.subreddit.wiki["control_panel"].content_md
        return self.crt_control_panel

    def set_control_panel(self, content):
        """
        Set control panel content
        """
        if self.crt_control_panel != content:
            logger.debug("Editing control panel for %s" % self)
            return self.subreddit.wiki["control_panel"].edit(content)

    def get_writable_wiki(self, wiki_page):
        """
        Returns the plugin that has writing rights for a wiki page
        """
        for page in self.wiki_pages[wiki_page]:
            if "w" in page.mode:
                return page