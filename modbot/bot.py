import configparser
from modbot.plugin import plugin_manager
from modbot.reddit_wrapper import set_credentials, set_input_type, set_signature

class bot():
    def __init__(self, bot_config_path, backend="reddit"):
        """
        Create a bot instance.
        :param bot_config_path: path for the bot config file
        :param backend: what backend to use to get submissions/comments
        """

        # Load config
        self.config = configparser.ConfigParser()
        self.config.read(bot_config_path)

        # Set how data is fetched (either live from reddit or from a test framework)
        set_input_type(backend)

        # Set PRAW options
        set_credentials(self.config.get("reddit", "praw_config_section"), self.config.get("reddit", "user_agent"))

        # Mark if running in test mode
        self.in_production = self.config.get("mode", "production", fallback=False)

        # DB credentials are optional - check if present
        db_credentials = None
        if "postgresql" in self.config.sections():
            db_credentials = self.config["postgresql"]

        # Set bot signature when sending messages
        owner = self.config.get("owner", "owner")

        set_signature(
            "\n\n***\n^^This ^^message ^^was ^^sent ^^by ^^a ^^bot. ^^For ^^more ^^details [^^send ^^a ^^message](https://www.reddit.com/message/compose?to=%s&subject=Bot&message=) ^^to ^^its ^^author." % owner)

        self.pmgr = plugin_manager(
            self,
            path_list=self.config.get("config", "plugin_folders").split(","),
            with_reload=self.config.get(section="debug", option="reload", fallback=False),
            bot_config=self.config,
            master_subreddit=self.config.get(section="config", option="master_subreddit"),
            db_params=db_credentials
        )