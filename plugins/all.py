from modbot import hook

@hook.submission
def callm(reddit, subreddit, submission):
    print(subreddit.title)

@hook.periodic(period="2")
def call3(reddit):
    pass
    print("per" + str(reddit))

@hook.comment
def callx(reddit, subreddit, comment):
    print("any comment at ", comment.subreddit)

@hook.comment(subreddit="Romania")
def call4(reddit, subreddit, comment):
    print("comment Romania " + comment.body)
