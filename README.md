**Build status**

master: [![Build Status](https://travis-ci.com/gc-plp/reddit-moderator-bot.svg?branch=master)](https://travis-ci.com/gc-plp/reddit-moderator-bot) [![codecov](https://codecov.io/gh/gc-plp/reddit-moderator-bot/branch/master/graph/badge.svg)](https://codecov.io/gh/gc-plp/reddit-moderator-bot)

dev: [![Build Status](https://travis-ci.com/gc-plp/reddit-moderator-bot.svg?branch=dev)](https://travis-ci.com/gc-plp/reddit-moderator-bot) [![codecov](https://codecov.io/gh/gc-plp/reddit-moderator-bot/branch/dev/graph/badge.svg)](https://codecov.io/gh/gc-plp/reddit-moderator-bot)

# Reddit moderator bot

This project is a reddit bot that can monitor subreddits and trigger custom actions through plugins.

Actions supported by plugins are triggered when:
  * a post is submitted in a comment
  * a comment is submitted in a subreddit
  * at a given period of time

For reference, there are a couple of plugin examples in plugins/.


In order to start up the bot, a config file named 'reddit-bot.ini' needs to be created.
Config file example:
```
# Set details about the bot owner - used for signing messages and
# forwarding messages received by the bot
[owner]
owner = i_am_the_bot_owner_and_this_is_an_invalid_username

[reddit]
user_agent = user agent to be used by the bot
praw_config_section = PRAW config section to use for authenticating the bot

[config]
master_subreddit = subreddit where debug logs are posted
# This should not be changed since all the plugins are in plugins/
plugin_folders = plugins

[postgresql]
# Set DB connection settings to psql
host = localhost
database = dbname
user = dbuser
password = dbpassword

# Add optional Discord webhook for each botlog() instance
[webhook_discord]
storage=https://discord.web.hook1
audit=https://discord.web.hook2
```
Then, make sure that you install all the prerequisites listed in requirements.txt.

Finally, you can run `python3 moderator-bot.py` to start the bot.

# How it works

1. When starting up, the bot will log in using the given credentials.

2. On each subreddit where the bot is a moderator, it will create a wiki page named `control_panel`. If your subreddit is called `test123`, then the page will be found at `https://www.reddit.com/r/test123/wiki/control_panel`

3. In the control panel you can enable/disable plugins and check the plugin status.

4. To enable a plugin you need to add it to the `[Enabled Plugins]` section, by copying the plugin name. Each plugin name is found in the bottom side of the page and contains a short description, a link to its configuration page and the current status.

5. Once you have copied the plugin name to the `[Enabled Plugins]` section, save the page and wait until the `Current Status` line is set to `Enabled`. This should take about 5 to 10 minutes.

6. To configure the newly enabled plugin, open the page referenced by the plugin, in the `control_panel` page.
