# Log all exceptions
import sys
import traceback
from modbot.log import botlog

logger = botlog("exception")


def log_exception(type, value, tb):
    trace = traceback.format_list(traceback.extract_tb(tb))
    logger.error(value.args[0] + "\n" + "".join(trace))

    original_hook(type, value, tb)


# Save the original hook and add a custom one
original_hook = sys.excepthook
sys.excepthook = log_exception
