from modbot import hook

@hook.submission()
def call_new_sub(db, submission):
    db.add_submission(submission)

@hook.comment()
def call_new_comment(comment, db):
    db.add_comment(comment)