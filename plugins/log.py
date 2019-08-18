import datetime
from modbot import hook

@hook.submission()
def call_new_sub(db, submission):
    print("new sub " + submission.subreddit.display_name)
    #db.add_submission(submission)

@hook.comment()
def call_new_comment(comment, db):
    print("new comment " + comment.subreddit.display_name)
    #db.add_comment(comment)

def call_me2():
    print("asd")

@hook.on_start
def call_me(schedule_call):
    schedule_call(call_me2, datetime.datetime.utcnow() + datetime.timedelta(days=1))

@hook.periodic(period=1)
def asd():
    pass
    #print("log")


@hook.comment(subreddit=["pics", "AskReddit"])
def xxx(db, comment):
    print("new ccccc " + comment.subreddit.display_name)
    #db.add_submission(submission)