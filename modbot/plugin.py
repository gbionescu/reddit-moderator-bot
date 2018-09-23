import os
import glob
import importlib
import threading
import logging
import time

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
    def __init__(self, path_list=None, reddit=None, with_reload=False, bot_config={}):
        """
        Class that manages plugins from a given list of paths.
        :param path_list: list of folders relative to the location from where
        :param reddit: reddit instance
        :param with_reload: True if plugin reloading shall be enabled
        :param bot_config: bot config data
        """
        self.modules = []
        self.callbacks_peri = []
        self.callbacks_subs = []
        self.callbacks_coms = []

        self.watch_threads = []
        self.per_last_exec = {}
        self.reddit = reddit
        self.config = bot_config
        self.with_reload = with_reload

        # Get notifications from the hook module
        callbacks.append(self.add_callback)

        for path in path_list:
            self.load_plugins(path)

        # Only use reloading in debug
        if with_reload:
            self.reloader = PluginReloader(self)
            self.reloader.start(path_list)

    def add_callback(self, func):
        """
        Add a callback function that was loaded from a plugin file
        :param func: function to add
        """
        self.load_callbacks([func])

    def load_plugin(self, fname):
        """
        Load a whole plugin file
        :param fname: file name to load
        """

        # Try unloading the file first
        self.unload_plugin(fname)
        self._load_plugin(fname)

    def _load_plugin(self, fname):
        """
        Load a plugin.
        """
        logger.debug("Loading %s" % fname)
        basename = os.path.basename(fname)
        pfile = os.path.splitext(fname)[0]

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
        """

        plugins = glob.iglob(os.path.join(path, '*.py'))
        for f in plugins:
            result = self._load_plugin(f)
            self.modules.append(result)

        self.create_periodic_thread(self.reddit)


    def load_callbacks(self, cbk_list):
        """
        load a list of callbacks
        """

        # Check each callback type
        for cbk in cbk_list:
            if cbk.ctype == callback_type.SUB:
                self.callbacks_subs.append(cbk)
            elif cbk.ctype == callback_type.COM:
                self.callbacks_coms.append(cbk)
            elif cbk.ctype == callback_type.PER:
                self.callbacks_peri.append(cbk)
                # If it's periodic, check if the first call should be delayed
                if hasattr(cbk, "first"):
                    first = int(cbk.first)
                    period = int(cbk.period)
                    # Put it in the last executed queue, as if it were executed
                    self.per_last_exec[cbk] = utils.utcnow() - (period - first)
            elif cbk.ctype == callback_type.ONC:
                # If callback is of type once, call it now
                cbk.func(self, self.reddit)


    def create_periodic_thread(self, reddit):
        """
        Create a thread that launches periodic events
        """
        periodic_thread = threading.Thread(
                name="pmgr_thread",
                target=self.periodic_func,
                args=(reddit,))

        periodic_thread.setDaemon(True)
        periodic_thread.start()

    def periodic_func(self, reddit):
        """
        Trigger periodic events
        """
        while True:
            tnow = utils.utcnow()

            # Go through periodic list
            for el in self.callbacks_peri:
                # If it was previously executed, check its time delta
                if el in self.per_last_exec:
                    if self.per_last_exec[el] + int(el.period) < tnow:
                        logger.debug("triggering " + str(el.func))

                        pthread = threading.Thread(
                                name="periodic",
                                target = el.func,
                                args=(self, reddit))

                        pthread.setDaemon(True)
                        pthread.start()

                        self.per_last_exec[el] = tnow

                else:
                    logger.debug("triggering " + str(el.func))
                    # Else run it now
                    pthread = threading.Thread(
                        name="periodic",
                        target = el.func,
                        args=(self, reddit))

                    pthread.setDaemon(True)
                    pthread.start()

                    self.per_last_exec[el] = tnow

            time.sleep(1)


    def watch_subs(self, sub_list):
        """
        Entry point that tells the plugin manager which subreddits to watch.
        Starts both submissions and comments watchers.
        """

        for sub in sub_list:
            logger.debug("Watching " + sub)
            sthread = threading.Thread(
                    name="submissions_%s" % sub,
                    target = self.thread_sub,
                    args=(self.reddit, sub))
            sthread.setDaemon(True)
            sthread.start()

            cthread = threading.Thread(
                    name="comments_%s" % sub,
                    target = self.thread_comm,
                    args=(self.reddit, sub))
            cthread.setDaemon(True)
            cthread.start()

            self.watch_threads.append(sthread)
            self.watch_threads.append(cthread)

    def thread_sub(self, reddit, sub):
        """
        Function used in threads that watch submissions
        """

        subreddit = reddit.subreddit(sub)

        for submission in subreddit.stream.submissions():
            self.feed_sub(reddit, submission.subreddit, submission)

    def thread_comm(self, reddit, sub):
        """
        Function used in threads that watch comments
        """

        subreddit = reddit.subreddit(sub)
        subreddit = reddit.subreddit(sub)

        for comment in subreddit.stream.comments():
            self.feed_comms(reddit, comment, comment.subreddit)

    def feed_sub(self, reddit, subreddit, submission):
        """
        Feeds a new submission to the plugin framework. This function calls
        plugins that match the submission.
        """

        # TODO use a dict
        for el in self.callbacks_subs:
            if el.subreddit == None or el.subreddit == subreddit:
                try:
                    el.func(reddit=reddit, subreddit=subreddit, submission=submission)
                except Exception as e:
                    logging.exception("Exception when running " + str(el.func))

    def feed_comms(self, reddit, comment, sub):
        """
        Feeds a new comment to the plugin framework. This function calls
        plugins that match the comment.
        """

        for el in self.callbacks_coms:
            if el.subreddit == None or el.subreddit == sub:
                try:
                    el.func(reddit=reddit, subreddit=sub, comment=comment)
                except Exception as e:
                    logging.exception("Exception when running " + str(el.func))
