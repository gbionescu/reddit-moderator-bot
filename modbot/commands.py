from modbot.log import botlog
from modbot.reddit_wrapper import get_moderator_users
from modbot import hook
from modbot.utils import BotThread

cmd_list = {}
cmd_list_raw = {}
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

def add_command(plugin_func):
    """
    Add an inbox command to the framework
    """
    if plugin_func.name in cmd_list:
        logger.error("Command %s already registered, ignoring" % plugin_func.name)
        return

    logger.debug("Adding command %s" % plugin_func.name)

    new_obj = command(
        plugin_func.func,
        plugin_func.name,
        plugin_func.doc,
        plugin_func.args)

    # Check if it should be added to the raw list or not
    if not plugin_func.raw:
        cmd_list[new_obj.name] = new_obj
    else:
        cmd_list_raw[new_obj.name] = new_obj

def set_prefix(prefix):
    """
    Set command prefix
    """
    global cmd_prefix

    logger.debug("Set prefix to " + prefix)
    cmd_prefix = prefix

def _call_target(target, message, plugin_args):
    call_args = {}

    avail_args = dict(plugin_args)
    avail_args["message"] = message

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

def execute_command(message, plugin_args):
    # Get the message body
    text = message.body

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
    for raw in cmd_list_raw.values():
        call_target(raw, message, plugin_args)

    # Run target command
    if not is_raw and text in cmd_list:
        # Check if the user can run this command
        right = get_rights_for_user(message.author, plugin_args["bot_owner"])
        if hook.has_rights_on(right, text):
            call_target(cmd_list[text], message, plugin_args)
        else:
            logger.error("User %s tried running unprivileged command %s" % (message.author, text))

def get_rights_for_user(user, bot_owner):
    rights = hook.permission.ANY
    if user.name == bot_owner.name:
        rights = hook.permission.OWNER
    elif user.name in get_moderator_users():
        rights = hook.permission.MOD

    return rights