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
```
