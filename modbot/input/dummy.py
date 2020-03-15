# Dummy input source


def set_praw_opts(credentials, user_agent):
    pass


def get_reddit(name="default", force_create=False):
    # TODO
    # move members calls
    # so that these classes are not needed
    class reddit():
        class ruser():
            name = "_"

            def moderator_subreddits(self):
                return []

            def redditor(self):
                pass

        class rsub():
            display_name = "_"
            pass

        def moderator_subreddits(self):
            pass

        def subreddit(self, *args, **kwargs):
            return self.rsub()

        def redditor(self, *args):
            return self.ruser()

        def __init__(self):
            self.user = self.ruser()

    return reddit()


def thread_sub(feeder):
    pass


def thread_comm(feeder):
    pass


def thread_reports(new_report):
    pass


def thread_modlog(modlog_func):
    pass


def get_wiki(subreddit, wiki_name):
    pass


def edit_wiki(subreddit, wiki_name, content):
    pass


def tick(period, trigger):
    pass
