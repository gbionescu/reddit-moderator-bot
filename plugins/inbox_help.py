from modbot import hook
from modbot.commands import cmd_list, get_rights_for_user
from modbot.hook import has_rights_on

@hook.command()
def help(message, bot_owner):
    """
    Returns help options through a PM
    """

    # Get rights for the user that sent the message
    rights = get_rights_for_user(message.author, bot_owner)

    reply = ""
    for command in cmd_list:
        if not has_rights_on(rights, command):
            continue
        reply += str(cmd_list[command]) + "\n\n"

    message.author.send_pm("Help", reply)

@hook.command()
def ping(message):
    """
    Sends 'pong' back
    """
    message.author.send_pm("pong", "Hey %s! Pong!" % message.author.name)