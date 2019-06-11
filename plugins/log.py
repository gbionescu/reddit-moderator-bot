from modbot import hook

@hook.submission()
def call_new_sub(db, submission):
    print("new sub")
    db.add_submission(submission)

@hook.comment()
def call_new_comment(comment, db):
    print("new comment")
    db.add_comment(comment)