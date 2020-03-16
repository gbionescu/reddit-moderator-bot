from modbot import hook
from modbot.commands import inbox_cmd_list, report_cmd_list, get_rights_for_user, cmd_prefix
from modbot.hook import has_rights_on


@hook.command()
def help(message, bot_owner):
    """
    Returns help options through a PM
    """

    item_prefix = "- " + cmd_prefix

    # Get rights for the user that sent the message
    rights = get_rights_for_user(message.author, bot_owner)

    pm_cmds = []
    rep_cmds = []

    # Make list of inbox commands
    for command in inbox_cmd_list:
        if not has_rights_on(rights, command):
            continue
        pm_cmds.append(command)

    # Make list of report commands
    for command in report_cmd_list:
        if not has_rights_on(rights, command):
            continue
        rep_cmds.append(command)

    reply = ""

    # Go through each list and build the reply
    if len(pm_cmds) > 0:
        reply += "Message commands:\n\n"
        for command in sorted(pm_cmds):
            reply += item_prefix + str(inbox_cmd_list[command]) + "\n\n"

    if len(rep_cmds) > 0:
        reply += "Report commands:\n\n"
        for command in sorted(rep_cmds):
            reply += item_prefix + str(report_cmd_list[command]) + "\n\n"

    message.author.send_pm("Help commands", reply)


@hook.command()
def ping(message):
    """
    Sends 'pong' back
    """
    message.author.send_pm("pong", "Hey %s! Pong!" % message.author.name)


@hook.report_command()
def ping2(report):
    """
    Sends 'pong' back
    """
    report.author.send_pm("pong2", "Hey %s! Pong!" % report.author.name)
