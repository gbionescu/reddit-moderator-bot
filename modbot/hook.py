import enum
from modbot.log import botlog
import inspect

callbacks = []
plugins_with_wikis = []
logger = botlog('hook')

@enum.unique
class subreddit_type(enum.Enum):
    MASTER_SUBREDDIT = 0 # References the master subreddit

@enum.unique
class callback_type(enum.Enum):
    SUB = 0
    COM = 1
    PER = 2
    ONL = 3
    ONS = 4

class plugin_function():
    def __init__(self, func, ctype, kwargs, path):
        """
        Object used to store information about a plugin function
        :param func: plugin_function function
        :param ctype: plugin_function type - see callback_type enum
        :param kwargs: keyword args
        """
        self.func = func
        self.ctype = ctype
        self.args = kwargs
        self.path = path
        self.args = inspect.getargspec(func)[0]

        self.wiki = None
        self.subreddit = None
        self.period = None
        self.first = None

        # Create attribute to track last time the hook was executed
        self.last_exec = 0

        if kwargs:
            # Check plugin_function type and parse parameters
            if 'subreddit' in kwargs:
                self.subreddit = kwargs['subreddit']

            if "wiki" in kwargs:
                self.wiki = kwargs["wiki"]
                self.subreddit = self.wiki.subreddits

            if ctype == callback_type.PER:
                if 'period' in kwargs:
                    self.period = kwargs['period']
                if 'first' in kwargs:
                    self.first = kwargs['first']

    def set_last_exec(self, mark):
        self.last_exec = mark

class PluginWiki():
    def __init__(self,
        wiki_page,
        description,
        documentation,
        wiki_change_notifier,
        subreddits,
        refresh_interval,
        mode,
        fpath,
        default_enabled):

        self.wiki_page = wiki_page
        self.description = description
        self.documentation = documentation
        self.wiki_change_notifier = wiki_change_notifier
        self.subreddits = subreddits
        self.refresh_interval = refresh_interval
        self.mode = mode
        self.path = fpath
        self.default_enabled = default_enabled

        logger.debug("Register wiki page " + wiki_page)

def register_wiki_page(
        wiki_page,
        description,
        documentation=None,
        wiki_change_notifier=None,
        subreddits=None,
        refresh_interval=60,
        mode="rw",
        default_enabled=False,
        ):
    """
    Register a plugin that has its own configuration page.
    """
    obj = PluginWiki(
                wiki_page=wiki_page,
                description=description,
                documentation=documentation,
                wiki_change_notifier=wiki_change_notifier,
                subreddits=subreddits,
                refresh_interval=refresh_interval,
                mode=mode,
                fpath=inspect.stack()[1][1],
                default_enabled=default_enabled
                )

    plugins_with_wikis.append(obj)

    return obj


def add_plugin_function(obj):
    """
    Generic function for adding a plugin_function to a plugin.
    """
    logger.debug("Add: " + str(obj.func) + " type " + str(obj.ctype) + " path " + obj.path)

    for func in callbacks:
        func(obj)

def submission(*args, **kwargs):
    """
    Submissions hook
    """
    def _command_hook(func):
        add_plugin_function(plugin_function(func, callback_type.SUB, kwargs, inspect.stack()[2][1]))
        return func

    # this decorator is being used directly
    if len(args) == 1 and callable(args[0]):
        add_plugin_function(plugin_function(args[0], callback_type.SUB, None, inspect.stack()[1][1]))
        return args[0]
    else:  # this decorator is being used indirectly, so return a decorator function
        return lambda func: _command_hook(func)

def periodic(*args, **kwargs):
    """
    Periodic hook
    """
    def _command_hook(func):
        add_plugin_function(plugin_function(func, callback_type.PER, kwargs, inspect.stack()[2][1]))
        return func

    # this decorator is being used directly
    if len(args) == 1 and callable(args[0]):
        add_plugin_function(plugin_function(args[0], callback_type.PER, None, inspect.stack()[1][1]))
        return args[0]
    else: # this decorator if being used indirectly, so return a decorator function
        return lambda func: _command_hook(func)

def comment(*args, **kwargs):
    """
    Comment hook
    """
    def _command_hook(func):
        add_plugin_function(plugin_function(func, callback_type.COM, kwargs, inspect.stack()[2][1]))
        return func

    # this decorator is being used directly
    if len(args) == 1 and callable(args[0]):
        add_plugin_function(plugin_function(args[0], callback_type.COM, None, inspect.stack()[1][1]))
        return args[0]
    else: # this decorator if being used indirectly, so return a decorator function
        return lambda func: _command_hook(func)

def on_load(*args, **kwargs):
    """
    On plugin load hook
    """
    def _command_hook(func):
        add_plugin_function(plugin_function(func, callback_type.ONL, kwargs, inspect.stack()[1][1]))
        return func

    # this decorator is being used directly
    if len(args) == 1 and callable(args[0]):
        add_plugin_function(plugin_function(args[0], callback_type.ONL, None, inspect.stack()[1][1]))
        return args[0]
    else: # this decorator if being used indirectly, so return a decorator function
        return lambda func: _command_hook(func)

def on_start(*args, **kwargs):
    """
    On bot start hook
    """
    def _command_hook(func):
        add_plugin_function(plugin_function(func, callback_type.ONS, kwargs, inspect.stack()[1][1]))
        return func

    # this decorator is being used directly
    if len(args) == 1 and callable(args[0]):
        add_plugin_function(plugin_function(args[0], callback_type.ONS, None, inspect.stack()[1][1]))
        return args[0]
    else: # this decorator if being used indirectly, so return a decorator function
        return lambda func: _command_hook(func)