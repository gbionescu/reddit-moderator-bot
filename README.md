
This project is a reddit bot that can monitor subreddits and trigger custom actions through plugins.

Actions supported by plugins are triggered when:
  * a post is submitted in a comment
  * a comment is submitted in a subreddit
  * at a given period of time

For reference, there are a couple of plugin examples in plugins/.


In order to start up the bot, a config file named 'reddit-bot.ini' needs to be created.
Config file example:
```
[debug]
# Comment to disable runtime plugin reloading
reload = true

[config]
# Configure what subreddits to watch for events
watch_subs = all
```
