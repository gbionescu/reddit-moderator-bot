import datetime
import threading

class BotThread():
    def __init__(self, target=None, name=None, args=()):
        self.obj = threading.Thread(
            target=target,
            name=name,
            args=args)

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

def set_time_source(func):
    global get_utcnow
    get_utcnow = func

def utcnow():
    return (get_utcnow() - datetime.datetime(1970, 1, 1)).total_seconds()

def date():
    return get_utcnow().strftime("%Y-%m-%d / %H:%M:%S")
