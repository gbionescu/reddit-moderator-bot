import enum
import logging
import inspect

callbacks = []
logger = logging.getLogger('plugin')

@enum.unique
class callback_type(enum.Enum):
    SUB = 0
    COM = 1
    PER = 2
    ONC = 3

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

        self.subreddit = None
        self.period = None
        self.first = None

        # Check plugin_function type and parse parameters
        if ctype == callback_type.SUB:
            if kwargs and 'subreddit' in kwargs:
                self.subreddit = kwargs['subreddit']
        elif ctype == callback_type.COM:
            if kwargs and 'subreddit' in kwargs:
                self.subreddit = kwargs['subreddit']
        elif kwargs and ctype == callback_type.PER:
            if 'period' in kwargs:
                self.period = kwargs['period']
            if 'first' in kwargs:
                self.first = kwargs['first']

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


def once(*args, **kwargs):
    """
    Comment hook
    """
    def _command_hook(func):
        add_plugin_function(plugin_function(func, callback_type.ONC, kwargs, inspect.stack()[1][1]))
        return func

    # this decorator is being used directly
    if len(args) == 1 and callable(args[0]):
        add_plugin_function(plugin_function(args[0], callback_type.ONC, None, inspect.stack()[1][1]))
        return args[0]
    else: # this decorator if being used indirectly, so return a decorator function
        return lambda func: _command_hook(func)
