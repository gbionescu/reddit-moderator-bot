from modbot import hook
from modbot.log import botlog

logger = botlog("cmd_forwarder")


@hook.command(raw=True)
def fwd_things(event, bot_owner, is_report):
    """
    Forwards incoming commands to the bot owner
    """
    if event.author.name == bot_owner.name:
        return

    if not is_report:
        logger.debug(
            f"Message received from {event.author}\nContent: {event.body}")
    else:
        logger.debug(f"Report command received from {event.author}\n\nContent: {event.body}\n\nLink: {event.permalink}")
