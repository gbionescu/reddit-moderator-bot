import datetime
from modbot import hook

@hook.command(raw=True)
def fwd_inbox(message, bot_owner):
    """
    Forwards incoming messages to the bot owner
    """
    bot_owner.send_pm(
        "Message received from %s" % message.author,
        "Content: %s" % message.body)