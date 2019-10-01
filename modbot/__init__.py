import praw
import configparser
from modbot.plugin import plugin_manager

class bot():
    def __init__(self, bot_config_path):
        """
        Create a bot instance.
        :param bot_config_path: path for the bot config file
        """

        # Load config
        self.config = configparser.ConfigParser()
        self.config.read(bot_config_path)

        # Create reddit instance
        self.reddit = praw.Reddit(
            self.config.get("reddit", "praw_config_section"),
            user_agent=self.config.get("reddit", "user_agent"))

        # Mark if running in test mode
        self.in_production = self.config.get("mode", "production", fallback=False)

        # Get list of moderated subreddits
        self.moderated_subs = []
        for i in self.reddit.user.moderator_subreddits():
            if i.display_name.startswith("u_"):
                continue

            self.moderated_subs.append(i.display_name)

        self.pmgr = plugin_manager(
            self,
            path_list=self.config.get("config", "plugin_folders").split(","),
            with_reload=self.config.get(section="debug", option="reload", fallback=False),
            bot_config=self.config,
            master_subreddit=self.config.get(section="config", option="master_subreddit"),
            db_params=dict(self.config["postgresql"])
        )

    def get_moderated_subs(self):
        return self.moderated_subs

    def get_subreddit(self, sub):
        return self.reddit.subreddit(sub)

    def send_pm(self, user, subject, text, skip_signature=False):

        if not skip_signature:
            text += "\n\n***\n^^This ^^message ^^was ^^sent ^^by ^^a ^^bot. ^^For ^^more ^^details [^^send ^^a ^^message](https://www.reddit.com/message/compose?to=programatorulupeste&subject=Bot&message=) ^^to ^^its ^^author."

        user.message(subject, text)

    def set_flair_id(self, post, flair_id):
        post.flair.select(flair_id)