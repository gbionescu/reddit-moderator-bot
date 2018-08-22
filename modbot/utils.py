import datetime

def utcnow():
    return (datetime.datetime.utcnow() - datetime.datetime(1970, 1, 1)).total_seconds()
