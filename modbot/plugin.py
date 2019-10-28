import os
import glob
import importlib
import threading
import time
import configparser
import logging
from oslo_concurrency.watchdog import watch
from database.db import db_data
from modbot import hook

# meh method of getting the callback list after loading, but works for now
from modbot.hook import callbacks, plugins_with_wikis
from modbot.hook import callback_type
from modbot.reloader import PluginReloader
from modbot import utils
from modbot.log import botlog
from modbot.moderated_sub import DispatchAll, DispatchSubreddit

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

        self.watch_dict = {} # maps watched subreddits to threads
        self.plugin_threads = []
        self.per_last_exec = {}
        self.bot = bot_inst
        self.config = bot_config
        self.with_reload = with_reload
        self.plugin_args = {}

        # Functions loaded by plugins
        self.plugin_functions = []

        # Dict of subreddit PRAW instances
        self.sub_instances = {}
        for sub in self.bot.get_moderated_subs():
            self.sub_instances[sub] = self.bot.get_subreddit(sub)

        self.master_sub = self.bot.get_subreddit(master_subreddit)

        # Save the given watched subreddits
        self.given_watched_subs = {}
        for sub in self.bot.get_moderated_subs():
            self.given_watched_subs[sub] = True

        self.watched_subs = dict(self.given_watched_subs)

        print("Connecting to DB")
        # Create DB connection
        self.db = db_data(
            "postgresql+psycopg2://{user}:{password}@{host}/{database}".format(**db_params))

        # Fill the standard parameter list
        self.plugin_args["plugin_manager"] = self
        self.plugin_args["config"] = self.config
        self.plugin_args["db"] = self.db
        self.plugin_args["schedule_call"] = self.schedule_call
        self.plugin_args["bot"] = self.bot
        self.plugin_args["send_pm"] = self.bot.send_pm
        self.plugin_args["reddit_inst"] = self.bot.reddit
        self.plugin_args["set_flair_id"] = self.bot.set_flair_id

        # Set start time
        self.start_time = utils.utcnow()

        print("Getting dispatchers")
        self.dispatchers = {}
        self.dispatchers[DISPATCH_ANY] = DispatchAll(self.plugin_args)

        # Get notifications from the hook module
        callbacks.append(self.add_plugin_function)

        print("Loading plugins")
        # Load plugins
        for path in path_list:
            self.load_plugins(path)

        # Only use reloading in debug
        if with_reload == "Yes":
            self.reloader = PluginReloader(self)
            self.reloader.start(path_list)

        print("Running on start plugins")
        self.dispatchers[DISPATCH_ANY].run_on_start(False)

        print("Creating periodic thread")
        # Create the periodic thread to trigger periodic events
        self.create_periodic_thread()

        print("Watching subs")
        self.watch_subs(self.watched_subs.keys())
        print("Startup done!")

    def get_subreddit(self, name):
        """
        Get PRAW instance for a subreddit
        """
        if name not in self.sub_instances:
            self.sub_instances[name] = self.bot.get_subreddit(name)

        return self.sub_instances[name]

    def schedule_call(self, func, when, args=[], kwargs={}):
        self.db.add_sched_event(func.__module__, func.__name__, args, kwargs, when)

    def add_plugin_function(self, func):
        """
        Add a function that was loaded from a plugin file

        :param func: function to add
        """
        self.plugin_functions.append(func)

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
                sub_list = self.bot.get_moderated_subs()

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

    def load_plugin(self, fname):
        """
        Wrapper for loading a plugin. First unloads and the loads the given file.

        :param fname: file name to load
        """

        # Try unloading the file first
        self.unload_plugin(fname)
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
            # Import the file
            plugin_module = importlib.import_module(plugin_name)

            # If file was previously imported, reload
            if plugin_module in self.modules:
                plugin_module = importlib.reload(plugin_module)

            # Return the imported file
            return plugin_module
        except Exception as e:
            import traceback
            logger.debug("Error loading %s:\n\t%s" %(fname, e))
            traceback.print_exc()
            return

    def unload_plugin(self, fname):
        """
        Unload a plugin.

        :param fname: unloads a plugin file
        """

        def rem_plugin(plist, path):
            for elem in plist:
                if elem.path == path:
                    logger.debug("Removing %s" % str(elem))
                    plist.remove(elem)

        logger.debug("Unloading %s" % fname)

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

    def create_periodic_thread(self):
        """
        Create a thread that launches periodic events
        """
        logger.debug("Starting periodic check thread")

        periodic_thread = threading.Thread(
                name="pmgr_thread",
                target=self.periodic_func)

        periodic_thread.setDaemon(True)
        periodic_thread.start()

    def periodic_func(self):
        """
        Trigger periodic events
        """
        while True:
            tnow = utils.utcnow()

            for dispatch in self.dispatchers.values():
                dispatch.run_periodic(self.start_time, tnow)

            # Wait 1s between checks
            time.sleep(0.2)

            # Account for threads
            for thr in self.plugin_threads.copy():
                if thr.is_alive():
                    logger.debug("thread %s is still alive" % thr.name)
                else:
                    self.plugin_threads.remove(thr)

    def watch_subs(self, sub_list):
        """
        Entry point that tells the plugin manager which subreddits to watch.
        Starts both submissions and comments watchers.

        :param sub_list: list of subreddits to watch
        """

        sub_list = list(sub_list)
        if "all" not in sub_list:
            sub_list.append("all")

        for sub in sub_list:
            if sub != "all":
                if self.bot.get_subreddit(sub).subreddit_type not in ["private", "user"]:
                    logger.debug("Skipping %s, because it's not a private subreddit and I'm watching /r/all" % sub)
                    continue

            logger.debug("Watching " + sub)
            sthread = threading.Thread(
                    name="submissions_%s" % sub,
                    target = self.thread_sub,
                    args=(sub,))
            sthread.setDaemon(True)
            sthread.start()

            cthread = threading.Thread(
                    name="comments_%s" % sub,
                    target = self.thread_comm,
                    args=(sub,))
            cthread.setDaemon(True)
            cthread.start()

            self.watch_dict[sub] = (sthread, cthread)

    def thread_sub(self, sub):
        """
        Watch submissions and trigger submission events

        :param sub: subreddit to watch
        """

        subreddit = self.bot.get_subreddit(sub)

        for submission in subreddit.stream.submissions():
            self.feed_sub(submission.subreddit, submission)

    def thread_comm(self, sub):
        """
        Watch comments and trigger comments events

        :param sub: subreddit to watch
        """

        subreddit = self.bot.get_subreddit(sub)

        for comment in subreddit.stream.comments():
            self.feed_comms(comment.subreddit, comment)

    def feed_sub(self, subreddit, submission):
        """
        Feeds a new submission to the plugin framework. This function calls
        plugins that match the submission.

        :param subreddit: subreddit where the submission was posted
        :param submission: submission instance
        """
        #logger.debug("[%s] New submission %s" % (subreddit.display_name, submission.shortlink))
        if self.given_watched_subs.get(subreddit.display_name, None):
            self.dispatchers[DISPATCH_ANY].run_submission(submission)

        disp = self.dispatchers.get(subreddit.display_name, None)
        if disp:
            self.dispatchers[subreddit.display_name].run_submission(submission)

    def feed_comms(self, subreddit, comment):
        """
        Feeds a new comment to the plugin framework. This function calls
        plugins that match the comment.

        :param subreddit: subreddit where the comment was posted
        :param submission: comment instance
        """

        if self.given_watched_subs.get(subreddit.display_name, None):
            self.dispatchers[DISPATCH_ANY].run_comment(comment)

        disp = self.dispatchers.get(subreddit.display_name, None)
        if disp:
            disp.run_comment(comment)
