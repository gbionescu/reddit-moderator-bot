import datetime

###############################################################################
# Clean up storage
###############################################################################
from modbot.storage import set_storage_loc, clean_storage_loc
clean_storage_loc("storage_test/")
set_storage_loc("storage_test/")

###############################################################################
# Override time get function
###############################################################################
from modbot.utils import set_time_source
GLOBAL_TIME = 0
def set_time(val):
    global GLOBAL_TIME
    GLOBAL_TIME = val

def advance_time(val):
    global GLOBAL_TIME
    set_time(GLOBAL_TIME + val)

def get_time():
    return datetime.datetime.fromtimestamp(GLOBAL_TIME)

# Override time source
set_time_source(get_time)

###############################################################################
# Set custom thread implementation
###############################################################################
import modbot.utils as utils
class TestThread():
    def __init__(self, target=None, name=None, args=()):
        self.name = name
        self.target = target
        self.args = args

    def setDaemon(self, state):
        pass

    def start(self):
        self.target(*self.args)

    def isAlive(self):
        return False

utils.BotThread = TestThread