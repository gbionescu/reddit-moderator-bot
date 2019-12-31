import os
import sys
import glob
import importlib
import time
import configparser
import logging
from oslo_concurrency.watchdog import watch
from database.db import db_data
from modbot import hook
from modbot.commands import add_command, execute_command

# meh method of getting the callback list after loading, but works for now
from modbot.hook import callbacks, plugins_with_wikis
from modbot.hook import callback_type
from modbot import utils
from modbot.log import botlog
from modbot.moderated_sub import DispatchAll, DispatchSubreddit
from modbot.reddit_wrapper import get_moderated_subs, get_subreddit, start_tick, get_submission, watch_all, get_user

logger = botlog("plugin")

DISPATCH_ANY = 0

class plugin_manager():
    # Dictionary of items that can be passed to plugins
    def __init__(self,
        bot_inst,
        master_subreddit,
        path_list=None,
        with_reload=False,
        bot_config={},
        db_params={}):
        """
        Class that manages plugins from a given list of paths.
        :param bot_inst: bot instance
        :param master_subreddit: subreddit where core bot configuration is stored
        :param path_list: list of folders relative to the location from where to load plugins
        :param with_reload: True if plugin reloading shall be enabled
        :param bot_config: bot config data
        :param db_params: how to log in to the psql server
        """
        self.modules = []

        self.plugin_threads = []
        self.per_last_exec = {}
        self.bot = bot_inst
        self.config = bot_config
        self.plugin_args = {}
        self.inbox_cmds = {}

        self.master_sub = get_subreddit(master_subreddit)

        # Save the given watched subreddits
        self.given_watched_subs = {}
        for sub in get_moderated_subs():
            self.given_watched_subs[sub] = True

        self.watched_subs = dict(self.given_watched_subs)

        self.db = None
        if db_params:
            print("Connecting to DB")
            # Create DB connection
            self.db = db_data(
                "postgresql+psycopg2://{user}:{password}@{host}/{database}".format(**db_params))

        # Fill the standard parameter list
        self.plugin_args["plugin_manager"] = self
        self.plugin_args["reddit"] = self
        self.plugin_args["config"] = self.config
        self.plugin_args["db"] = self.db
        self.plugin_args["schedule_call"] = self.schedule_call
        self.plugin_args["bot_owner"] = get_user(self.config.get("owner", "owner"))

        # Set start time
        self.start_time = utils.utcnow()

        print("[%d] Getting dispatchers" % utils.utcnow())
        self.dispatchers = {}
        self.dispatchers[DISPATCH_ANY] = DispatchAll(self.plugin_args)

        # Get notifications from the hook module
        callbacks.append(self.add_plugin_function)

        print("[%d] Loading plugins" % utils.utcnow())
        # Load plugins
        for path in path_list:
            self.load_plugins(path)

        print("[%d] Running on start plugins" % utils.utcnow())
        self.dispatchers[DISPATCH_ANY].run_on_start(False)

        print("[%d] Creating periodic thread" % utils.utcnow())
        # Create the periodic thread to trigger periodic events
        start_tick(1.0, self.periodic_func)

        print("[%d] Startup done!" % utils.utcnow())

        # Start watching subreddits
        watch_all(self.feed_sub, self.feed_comms, self.feed_inbox)

    def get_subreddit(self, name):
        return get_subreddit(name)

    def get_moderated_subs(self):
        return get_moderated_subs()

    def get_submission(self, url):
        return get_submission(url)

    def schedule_call(self, func, when, args=[], kwargs={}):
        self.db.add_sched_event(func.__module__, func.__name__, args, kwargs, when)

    def add_reddit_function(self, func):
        # Check if we should add it to the generic dispatcher or a specific one
        if func.subreddit == None and func.wiki == None:
            self.dispatchers[DISPATCH_ANY].add_callback([func])
        else:
            sub_list = []
            # Check if it's a list or a string
            if type(func.subreddit) == str:
                sub_list = [func.subreddit]
            elif type(func.subreddit) == list:
                sub_list = func.subreddit

            # If nothing was specified, then the plugin is active on all moderated subs
            if sub_list == []:
                sub_list = get_moderated_subs()

            for sub in sub_list:
                if sub == hook.subreddit_type.MASTER_SUBREDDIT:
                    func.wiki.subreddits = [self.master_sub]
                    sub = self.master_sub.display_name
                if sub not in self.dispatchers:
                    logger.debug("Creating dispatcher for subreddit: " + sub)
                    self.dispatchers[sub] = \
                        DispatchSubreddit(self.get_subreddit(sub), self.plugin_args)

                self.dispatchers[sub].add_callback([func])

                if sub not in self.watched_subs:
                    self.watched_subs[sub] = True

    def add_inbox_cmd(self, func):
        add_command(func)

    def add_plugin_function(self, func):
        """
        Add a function that was loaded from a plugin file

        :param func: function to add
        """

        # Bot commands should go through another path
        if func.ctype == callback_type.CMD:
            self.add_inbox_cmd(func)
        else:
            self.add_reddit_function(func)

    def load_plugin(self, fname):
        """
        Wrapper for loading a plugin.

        :param fname: file name to load
        """

        self._load_plugin(fname)

    def _load_plugin(self, fname):
        """
        Load a plugin.

        :param file: plugin file to load
        :return: importlib import_module instance
        """
        logger.debug("Loading %s" % fname)
        basename = os.path.basename(fname)

        # Build file name
        plugin_name = "%s.%s" % (os.path.basename(os.path.dirname(fname)), basename)
        plugin_name = plugin_name.replace(".py", "")

        try:
            plugin_module = None
            # If file was previously imported, reload
            if plugin_module in self.modules or plugin_name in sys.modules.keys():
                plugin_module = importlib.reload(importlib.import_module(plugin_name))
            else:
                # Import the file
                plugin_module = importlib.import_module(plugin_name)

            # Return the imported file
            return plugin_module
        except Exception as e:
            import traceback
            logger.debug("Error loading %s:\n\t%s" %(fname, e))
            traceback.print_exc()
            return

    def load_plugins(self, path):
        """
        Load plugins from a specified path.

        :param path: globs over python files in a path and loads each one
        """

        logger.debug("Loading plugins from %s" % path)
        plugins = glob.iglob(os.path.join(path, '*.py'))
        for f in plugins:
            result = self._load_plugin(f)
            self.modules.append(result)

    def periodic_func(self, tnow):
        """
        Trigger periodic events
        """

        for dispatch in self.dispatchers.values():
            dispatch.run_periodic(self.start_time, tnow)

        # Account for threads
        for thr in self.plugin_threads.copy():
            if thr.is_alive():
                logger.debug("thread %s is still alive" % thr.name)
            else:
                self.plugin_threads.remove(thr)

    def feed_sub(self, submission):
        """
        Feeds a new submission to the plugin framework. This function calls
        plugins that match the submission.

        :param subreddit: subreddit where the submission was posted
        :param submission: submission instance
        """

        #if self.given_watched_subs.get(submission.subreddit_name, None):
        self.dispatchers[DISPATCH_ANY].run_submission(submission)

        disp = self.dispatchers.get(submission.subreddit_name, None)
        if disp:
            self.dispatchers[submission.subreddit_name].run_submission(submission)

    def feed_comms(self, comment):
        """
        Feeds a new comment to the plugin framework. This function calls
        plugins that match the comment.

        :param subreddit: subreddit where the comment was posted
        :param submission: comment instance
        """

        # TODO clean up watched_subs
        #if self.given_watched_subs.get(comment.subreddit_name, None):
        self.dispatchers[DISPATCH_ANY].run_comment(comment)

        disp = self.dispatchers.get(comment.subreddit_name, None)
        if disp:
            disp.run_comment(comment)

    def feed_inbox(self, message):
        """
        Feeds an inbox message
        """

        execute_command(message, self.plugin_args)
