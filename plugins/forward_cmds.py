import datetime
from modbot import hook


@hook.command(raw=True)
def fwd_things(event, bot_owner, is_report):
    """
    Forwards incoming commands to the bot owner
    """
    if event.author.name == bot_owner.name:
        return

    if not is_report:
        bot_owner.send_pm(
            "Message received from %s" % event.author,
            "Content: %s" % event.body)
    else:
        bot_owner.send_pm(
            "Report command received from %s" % (event.author),
            "Content: %s\n\nLink: %s" % (event.body, event.permalink))
