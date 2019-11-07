import configparser
from modbot.plugin import plugin_manager
from modbot.reddit import set_praw_opts

class bot():
    def __init__(self, bot_config_path):
        """
        Create a bot instance.
        :param bot_config_path: path for the bot config file
        """

        # Load config
        self.config = configparser.ConfigParser()
        self.config.read(bot_config_path)

        # Set PRAW options
        set_praw_opts(self.config.get("reddit", "praw_config_section"), self.config.get("reddit", "user_agent"))

        # Mark if running in test mode
        self.in_production = self.config.get("mode", "production", fallback=False)

        # DB credentials are optional - check if present
        db_credentials = None
        if "postgresql" in self.config.sections():
            db_credentials = self.config["postgresql"]

        self.pmgr = plugin_manager(
            self,
            path_list=self.config.get("config", "plugin_folders").split(","),
            with_reload=self.config.get(section="debug", option="reload", fallback=False),
            bot_config=self.config,
            master_subreddit=self.config.get(section="config", option="master_subreddit"),
            db_params=db_credentials
        )