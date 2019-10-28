import datetime

class timedata:
    SEC_IN_MIN = 60
    MIN_IN_HOUR = 60
    HOUR_IN_DAY = 24

    SEC_IN_DAY = SEC_IN_MIN * MIN_IN_HOUR * HOUR_IN_DAY

def utcnow():
    return (datetime.datetime.utcnow() - datetime.datetime(1970, 1, 1)).total_seconds()

def date():
    return datetime.datetime.utcnow().strftime("%Y-%m-%d / %H:%M:%S")
