import datetime

def utcnow():
    return (datetime.datetime.utcnow() - datetime.datetime(1970, 1, 1)).total_seconds()

def date():
    return datetime.datetime.utcnow().strftime("%Y-%m-%d / %H:%M:%S")
