import datetime
from modbot import hook

# @hook.submission()
# def call_new_sub(db, submission):
#     print("new sub")
#     #db.add_submission(submission)
# 
# @hook.comment()
# def call_new_comment(comment, db):
#     print("new comment")
#     #db.add_comment(comment)

def call_me2():
    print("asd")

@hook.on_start
def call_me(schedule_call):
    schedule_call(call_me2, datetime.datetime.utcnow() + datetime.timedelta(days=1))
