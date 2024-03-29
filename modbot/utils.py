import datetime
import threading
import configparser
import tzcron
import pytz


class BotThread():
    """
    Wrapper over Thread class
    """

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
        self.obj.is_alive()


class timedata:
    """
    Utilities for time ranges
    """
    SEC_IN_MIN = 60
    MIN_IN_HOUR = 60
    HOUR_IN_DAY = 24

    SEC_IN_DAY = SEC_IN_MIN * MIN_IN_HOUR * HOUR_IN_DAY
    SEC_IN_WEEK = SEC_IN_DAY * 7


def get_utcnow():
    """
    Wraps datetime.utcnow calls
    """
    return pytz.utc.localize(datetime.datetime.utcnow())


def utcnow():
    """
    Returns number of seconds since 1/1/1970
    """
    return (get_utcnow() - datetime.datetime(1970, 1, 1, tzinfo=pytz.utc)).total_seconds()

def timestamp_string(timestamp):
    """
    Converts a timestamp to string
    """
    date = pytz.utc.localize(datetime.datetime.fromtimestamp(timestamp))

    return date.strftime("%Y-%m-%d / %H:%M:%S") + " " + str(date.tzinfo)

def timestamp_to_datetime(timestamp):
    """
    Converts a timestamp to python datetime
    """
    return pytz.utc.localize(datetime.datetime.fromtimestamp(timestamp))

def date():
    """
    Returns current date as formatted string
    """
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
    """
    Calculate how much two lists overlap.
    """
    v1, v2 = calc_overlap(list1, list2)

    return (v1 + v2) / 2


def parse_wiki_content(crt_content, parser="CFG_INI"):
    """
    Parses given content depending on the type
    """
    if parser == "CFG_INI":
        parser = configparser.ConfigParser(allow_no_value=True, strict=False)
        try:
            parser.read_string(crt_content)
        except configparser.MissingSectionHeaderError:
            # All configs should contain [Setup]
            # If not, try prepending it
            if "[Setup]" not in crt_content:
                crt_content = "[Setup]\n" + crt_content

        # Try again
        try:
            parser.read_string(crt_content)
        except:
            return None

        return parser


def prepare_wiki_content(content, indented=True):
    """
    Set wiki page content
    """
    if indented:
        lines = content.split("\n")
        content = "    ".join(i + "\n" for i in lines)

    return content


def cron_next(param):
    # Get current date as set by the source
    time_now = pytz.utc.localize(datetime.datetime.utcfromtimestamp(utcnow()))

    # Get next trigger time
    next_dt = next(tzcron.Schedule(param, pytz.utc, time_now))

    # Return when the next trigger will happen in seconds
    return (next_dt - datetime.datetime(1970, 1, 1, tzinfo=pytz.utc)).total_seconds()


def remove_quotes(s):
    """
    Remove beginning/ending quotes from a string
    """

    if s.startswith('"') and s.endswith('"'):
        return s[1:-1]

    if s.startswith("'") and s.endswith("'"):
        return s[1:-1]

    return s