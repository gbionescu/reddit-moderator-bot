import configparser
import os
import sys
import modbot.ytaccess as yt

from modbot.log import add_discord_webhook
from modbot.plugin import plugin_manager
from modbot.reddit_wrapper import set_credentials, set_input_type, set_signature

class bot():
    def __init__(self, bot_config_path, backend="reddit"):
        """
        Create a bot instance.
        :param bot_config_path: path for the bot config file
        :param backend: what backend to use to get submissions/comments
        """

        if not os.path.isfile(bot_config_path):
            print("%s does not exist" % bot_config_path)
            sys.exit(0)

        # Load config
        self.config = configparser.ConfigParser()
        self.config.read(bot_config_path)

        # Set how data is fetched (either live from reddit or from a test framework)
        set_input_type(backend)

        # Set PRAW options
        set_credentials(self.config.get(
            "reddit", "praw_config_section"), self.config.get("reddit", "user_agent"))

        # DB credentials are optional - check if present
        db_credentials = None
        if "postgresql" in self.config.sections():
            db_credentials = self.config["postgresql"]

        # Set bot signature when sending messages
        owner = self.config.get("owner", "owner")
        set_signature(
            "\n\n***\n^^This ^^message ^^was ^^sent ^^by ^^a ^^bot. ^^For ^^more ^^details [^^send ^^a ^^message](https://www.reddit.com/message/compose?to=%s&subject=Bot&message=) ^^to ^^its ^^author." % owner)

        # Get the discord webhook section if set
        if "webhook_discord" in self.config:
            for item in self.config["webhook_discord"]:
                # for each item in the section, add the corresponding hook
                add_discord_webhook(item, self.config["webhook_discord"][item])

        yt.devkey = self.config.get("youtube", "dev")

        self.pmgr = plugin_manager(
            self,
            path_list=self.config.get("config", "plugin_folders").split(","),
            bot_config=self.config,
            master_subreddit=self.config.get(
                section="config", option="master_subreddit"),
            db_params=db_credentials)
