from modbot.log import botlog
from modbot.reddit_wrapper import get_moderator_users
from modbot import hook
from modbot.utils import BotThread

inbox_cmd_list = {}
report_cmd_list = {}
raw_cmd_list = {}
cmd_prefix = "/"

logger = botlog("commands")

class command():
    def __repr__(self):
        return "%s - %s" % (self.name, self.doc.strip())

    def __init__(self, func, name, documentation, requested_args):
        self.func = func
        self.name = name
        self.doc = documentation
        self.requested_args = requested_args

def add_inbox_command(plugin_func):
    """
    Add an inbox command to the framework
    """
    if plugin_func.name in inbox_cmd_list:
        logger.error("Command %s already registered, ignoring" % plugin_func.name)
        return

    logger.debug("Adding inbox command %s" % plugin_func.name)

    new_obj = command(
        plugin_func.func,
        plugin_func.name,
        plugin_func.doc,
        plugin_func.args)

    # Check if it should be added to the raw list or not
    if not plugin_func.raw:
        inbox_cmd_list[new_obj.name] = new_obj
    else:
        raw_cmd_list[new_obj.name] = new_obj

def add_report_command(plugin_func):
    """
    Add an report command to the framework
    """
    if plugin_func.name in report_cmd_list:
        logger.error("Command %s already registered, ignoring" % plugin_func.name)
        return

    logger.debug("Adding inbox command %s" % plugin_func.name)

    new_obj = command(
        plugin_func.func,
        plugin_func.name,
        plugin_func.doc,
        plugin_func.args)

    # Check if it should be added to the raw list or not
    if not plugin_func.raw:
        report_cmd_list[new_obj.name] = new_obj
    else:
        raw_cmd_list[new_obj.name] = new_obj

def set_prefix(prefix):
    """
    Set command prefix
    """
    global cmd_prefix

    logger.debug("Set prefix to " + prefix)
    cmd_prefix = prefix

def _call_target(target, message, avail_args):
    call_args = {}

    # Build function parameters
    for req in target.requested_args:
        if req not in avail_args:
            raise ValueError("Parameter %s does not exist when calling %s" % (req, target.func))
        call_args[req] = avail_args[req]

    try:
        target.func(**call_args)
    except:
        import traceback
        traceback.print_exc()

def call_target(target, message, plugin_args):
    """
    Launch a thread for each plugin
    """
    BotThread(_call_target,
        "inbox_plugin",
        (target, message, plugin_args,))

def execute_list(item, plugin_args, cmd_list):
    # Get the body
    text = item.body

    # Check if it's correct
    if len(text) == 0:
        return None

    logger.debug("Executing command %s" % text)

    # Check if it's a raw command
    is_raw = True
    if text[0] == cmd_prefix:
        is_raw = False
        text = text[1:]

    # Run raw commands first
    for raw in raw_cmd_list.values():
        call_target(raw, item, plugin_args)

    # Run target command
    if not is_raw and text in cmd_list:
        # Check if the user can run this command
        right = get_rights_for_user(item.author, plugin_args["bot_owner"])
        if hook.has_rights_on(right, text):
            call_target(cmd_list[text], item, plugin_args)
        else:
            logger.error("User %s tried running unprivileged command %s" % (item.author, text))

def execute_report_command(report, plugin_args):
    args = dict(plugin_args)
    args["is_report"] = True
    args["report"] = report
    args["event"] = report
    execute_list(report, args, report_cmd_list)

def execute_inbox_command(message, plugin_args):
    args = dict(plugin_args)
    args["is_report"] = False
    args["message"] = message
    args["event"] = message
    execute_list(message, args, inbox_cmd_list)

def get_rights_for_user(user, bot_owner):
    rights = hook.permission.ANY
    if user.name == bot_owner.name:
        rights = hook.permission.OWNER
    elif user.name in get_moderator_users():
        rights = hook.permission.MOD

    return rights