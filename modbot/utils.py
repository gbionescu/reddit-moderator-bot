import datetime
import threading

class BotThread():
    def __init__(self, target=None, name=None, args=()):
        self.obj = threading.Thread(
            target=target,
            name=name,
            args=args)

        self.setDaemon(True)
        self.start()

    def setDaemon(self, state):
        self.obj.setDaemon(state)

    def start(self):
        self.obj.start()

    def isAlive(self):
        self.obj.isAlive()

class timedata:
    SEC_IN_MIN = 60
    MIN_IN_HOUR = 60
    HOUR_IN_DAY = 24

    SEC_IN_DAY = SEC_IN_MIN * MIN_IN_HOUR * HOUR_IN_DAY

def get_utcnow():
    return datetime.datetime.utcnow()

def utcnow():
    return (get_utcnow() - datetime.datetime(1970, 1, 1)).total_seconds()

def date():
    return get_utcnow().strftime("%Y-%m-%d / %H:%M:%S")

def calc_overlap(list1, list2):
    """
    Calculate how much two lists overlap percentage wise
    """
    if len(list1) > 0 and len(list2) > 0:
        return \
            (1.0 - len(set(list1).difference(set(list2))) / len(list1)) * 100, \
            (1.0 - len(set(list2).difference(set(list1))) / len(list2)) * 100
    return 0, 0

def calc_overlap_avg(list1, list2):
    v1, v2 = calc_overlap(list1, list2)

    return (v1 + v2) / 2