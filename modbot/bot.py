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
        self.config.read("reddit-bot.ini")

        # Create reddit instance
        self.reddit = praw.Reddit(
            self.config.get("reddit", "praw_config_section"),
            user_agent=self.config.get("reddit", "user_agent"))

        self.pmgr = plugin_manager(
            path_list=self.config.get("config", "plugin_folders").split(","),
            reddit=self.reddit,
            with_reload=self.config.get(section="debug", option="reload", fallback=False),
            bot_config=self.config,
            watch_subs=self.config.get(section="config", option="watch_subs").split(","),
            db_params=dict(self.config["postgresql"])
        )

