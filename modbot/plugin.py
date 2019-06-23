import os
import glob
import importlib
import threading
import logging
import time

from database.db import db_data
from modbot.reloader import PluginReloader

# meh method of getting the callback list after loading, but works for now
from modbot.hook import callbacks
from modbot.hook import callback_type
from modbot import utils

logger = logging.getLogger('plugin')
logger.setLevel(logging.DEBUG)

ch = logging.StreamHandler()
ch.setLevel(logging.DEBUG)

formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
ch.setFormatter(formatter)

fh = logging.FileHandler("bot.log")
fh.setLevel(logging.DEBUG)
fh.setFormatter(formatter)

logger.addHandler(ch)
logger.addHandler(fh)

class plugin_manager():
    # Dictionary of items that can be passed to plugins
    def __init__(self,
        bot_inst,
        path_list=None,
        with_reload=False,
        bot_config={},
        watch_subs=[],
        db_params={}):
        """
        Class that manages plugins from a given list of paths.
        :param bot_inst: bot instance
        :param path_list: list of folders relative to the location from where to load plugins
        :param with_reload: True if plugin reloading shall be enabled
        :param bot_config: bot config data
        :param watch_subs: subreddits to watch
        :param db_params: how to log in to the psql server
        """
        self.modules = []
        self.callbacks_peri = []
        self.callbacks_subs = []
        self.callbacks_coms = []

        self.watch_threads = []
        self.plugin_threads = []
        self.per_last_exec = {}
        self.bot = bot_inst
        self.config = bot_config
        self.with_reload = with_reload
        self.plugin_args = {}

        # Create DB connection
        self.db = db_data(
            "postgresql+psycopg2://{user}:{password}@{host}/{database}".format(**db_params))

        # Fill the standard parameter list
        self.add_plugin_arg(self, "bot")
        self.add_plugin_arg(self.config, "config")
        self.add_plugin_arg(self.db, "db")
        self.add_plugin_arg(self.schedule_call, "schedule_call")

        # Set start time
        self.start_time = utils.utcnow()

        # Get notifications from the hook module
        callbacks.append(self.add_plugin_function)

        for path in path_list:
            self.load_plugins(path)

        # Create the periodic thread to trigger periodic events
        self.create_periodic_thread()

        # Only use reloading in debug
        if with_reload:
            self.reloader = PluginReloader(self)
            self.reloader.start(path_list)

        self.watch_subs(watch_subs)

    def add_plugin_arg(self, object, alias):
        """
        Register an object as a plugin argument
        """
        if alias not in self.plugin_args:
            self.plugin_args[alias] = object

    def schedule_call(self, func, when, args=[], kwargs={}):
        self.db.add_sched_event(func.__module__, func.__name__, args, kwargs, when)

    def add_plugin_function(self, func):
        """
        Add a function that was loaded from a plugin file

        :param func: function to add
        """
        self.load_plugin_functions([func])

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

        rem_plugin(self.callbacks_subs, fname)
        rem_plugin(self.callbacks_coms, fname)
        rem_plugin(self.callbacks_peri, fname)


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

    def load_plugin_functions(self, func_list):
        """
        Stores a list of plugin functions depending on how each function is
        triggered: on submissions, on comments, periodic or once.

        :param func_list: list of plugin functions to load
        """

        # Check each callback type
        for cbk in func_list:
            if cbk.ctype == callback_type.SUB:
                self.callbacks_subs.append(cbk)

            elif cbk.ctype == callback_type.COM:
                self.callbacks_coms.append(cbk)

            elif cbk.ctype == callback_type.PER:
                self.callbacks_peri.append(cbk)

            elif cbk.ctype == callback_type.ONC:
                # If callback is of type once, call it now
                self.call_plugin_func(cbk, self.plugin_args)


    def create_periodic_thread(self):
        """
        Create a thread that launches periodic events
        """
        periodic_thread = threading.Thread(
                name="pmgr_thread",
                target=self.periodic_func)

        periodic_thread.setDaemon(True)
        periodic_thread.start()

    def periodic_func(self):
        """
        Trigger periodic events
        """
        def trigger_function(el):
            logger.debug("triggering " + str(el.func))

            pthread = threading.Thread(
                name="periodic_" + str(el.func),
                target = self.call_plugin_func,
                args=(el, self.args,))

            pthread.setDaemon(True)
            pthread.start()

            self.plugin_threads.append(pthread)
            self.per_last_exec[el] = tnow

        while True:
            tnow = utils.utcnow()

            # Go through periodic list
            for el in self.callbacks_peri:
                # Trigger it at the 'first' interval initially
                if el.first is not None:
                    if self.start_time + int(el.first) < tnow:
                        trigger_function(el)

                        # Delete the attribute so that it's not triggered again
                        el.first = None

                elif el.period is not None:
                    # If it was previously executed, check its time delta
                    if el in self.per_last_exec:
                        # Check if 'period' has passed since last executed
                        if self.per_last_exec[el] + int(el.period) < tnow:
                            trigger_function(el)
                    else:
                        trigger_function(el)

            # Wait 1s between checks
            time.sleep(1)

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

        for sub in sub_list:
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

            self.watch_threads.append(sthread)
            self.watch_threads.append(cthread)

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

    def feed_sub(self, subreddit, submission):
        """
        Feeds a new submission to the plugin framework. This function calls
        plugins that match the submission.

        :param subreddit: subreddit where the submission was posted
        :param submission: submission instance
        """

        # TODO use a dict
        for el in self.callbacks_subs:
            if el.subreddit == None or el.subreddit == subreddit:
                args = self.plugin_args.copy()
                args["subreddit"] = subreddit
                args["submission"] = submission

                self.call_plugin_func(el, args)

    def feed_comms(self, subreddit, comment):
        """
        Feeds a new comment to the plugin framework. This function calls
        plugins that match the comment.

        :param subreddit: subreddit where the comment was posted
        :param submission: comment instance
        """

        for el in self.callbacks_coms:
            if el.subreddit == None or el.subreddit == subreddit:
                args = self.plugin_args.copy()
                args["subreddit"] = subreddit
                args["comment"] = comment

                self.call_plugin_func(el, args)
