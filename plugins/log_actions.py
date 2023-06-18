from modbot import hook
from modbot.reddit_wrapper import get_item
from modbot.usernotes import get_unotes
from modbot.log import botlog
from modbot.utils import parse_wiki_content, remove_quotes

plugin_documentation = """
Take actions based on user notes.

When a new modlog item is appended to the modlog, take specific actions if the user has a specific usernote ONLY IF this item is present in the modqueue.

These are the actions supported:
- approve - approve an item
- remove - removes an item

How it works:
When a modlog item is found, it's checked against all config sections.
In the first example below the item is approved if the moderator that took the action "removecomment" is named "some_moderator", and if the user category "cats" contains an item named "this needs to be approved".

Example:
   [approve_things]
   mod_name = "some_moderator"
   removal_details = "bla bla bla"
   removal_action = "removecomment"
   take_action_on_note_category = "cats"
   take_action_on_note_content = "this needs to be approved"
   take_action = "approve"

   [remove_things]
   mod_name = "some_moderator11"
   removal_details = "xxx"
   removal_action = "removecomment"
   take_action_on_note_category = "some usernote category"
   take_action_on_note_content = "this needs to be removed"
   take_action = "remove"
"""
logger = botlog("log_action_plugin")

# Store wiki configuration per subreddit
wiki_config = {}


class LogAction():
    # What are the required fields inside a section
    required_fields = [
        "mod_name",
        "removal_details",
        "removal_action",
        "take_action_on_note_category",
        "take_action_on_note_content",
        "take_action"]

    def __init__(self, data, name):
        # Validate the section
        for field in self.required_fields:
            if field not in data:
                raise Exception(f"Could not find section {field} in {str(data)}")

        self.name = name
        self._data = {}
        for key, val in data.items():
            self._data[key] = remove_quotes(str(data[key]).strip())

    def matches(self, item):
        """
        Return True if the item matches this.
        """
        # First check if the initial conditions match
        if item.mod_name == self._data["mod_name"] and \
            item.details == self._data["removal_details"] and \
            item.action == self._data["removal_action"]:

            # Check if the usernotes match the condition
            mod_data, user_data = get_unotes(item.subreddit_name)
            if item.target_author in user_data:
                # Decapsulate mod toolbox items
                notes = user_data[item.target_author]
                for note in notes['ns']:
                    # If note name is the one given and note warning category is the one given, it's a match
                    if note['n'] != self._data["take_action_on_note_content"]:
                        continue

                    warning_num = note["w"]
                    if warning_num < len(mod_data["warnings"]) and mod_data["warnings"][warning_num] == self._data["take_action_on_note_category"]:
                        return True

        return False

    def take_action(self, item):
        actionable = get_item(item.target_fullname)
        if self._data["take_action"] == "approve":
            actionable.approve()
        elif self._data["take_action"] == "remove":
            actionable.remove()


def wiki_changed(sub, change):
    logger.debug("Wiki changed for log_actions, subreddit %s" % sub)
    cont = parse_wiki_content(change.content)

    if not cont:
        change.author.send_pm(
            "Error parsing the updated wiki page on %s" % sub)
        return

    configs = []
    try:
        # Read each section
        for section in cont:
            if section == "DEFAULT":
                continue
            # Add it to config
            configs.append(LogAction(cont[section], section))
    except Exception as e:
        change.author.send_pm(
            "Error parsing the updated wiki page on %s" % sub, str(e))

    # Save the config
    wiki_config[sub.display_name] = configs
    logger.debug("Added config to wiki_config. Current list: %s" %
                 str(wiki_config.keys()))


wiki = hook.register_wiki_page(
    wiki_page="log_action",
    description="Take actions on modlog items",
    documentation=plugin_documentation,
    wiki_change_notifier=wiki_changed)


@hook.modqueue(wiki=wiki)
def on_modqueue(modqueue, subreddit_name):
    if subreddit_name not in wiki_config:
        return

    for action in wiki_config[subreddit_name]:
        if action.matches(modqueue):
            action.take_action(modqueue)
            logger.debug(f"Took action {action.name} on {modqueue.target_permalink}")
            return

@hook.modlog(wiki=wiki)
def new_modlog_item(modlog, subreddit_name):
    # If the subreddit was not configured, skip
    if subreddit_name not in wiki_config:
        return

    for action in wiki_config[subreddit_name]:
        if action.matches(modlog):
            action.take_action(modlog)
            logger.debug(f"Took action {action.name} on {modlog.target_permalink}")
            return
