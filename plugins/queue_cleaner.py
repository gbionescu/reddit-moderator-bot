import datetime

from modbot import hook
from modbot.reddit_wrapper import scrape_modqueue, submission, comment, get_user
from modbot.log import botlog, send_to_discord
from modbot.utils import parse_wiki_content, remove_quotes, get_utcnow

plugin_documentation = """
Performs automatic actions on the modqueue based on the configuration in the
wiki page `queue_cleaner_config`. The configuration is a list of sections
with the following parameters:

* `type`: The type of item to perform the action on. Can be `submission`,
    `comment`, `automoderator`, `item_notification` or `user_notification`.

For each type, the following parameters are available:
    - comment:
        Takes action on comments in the modqueue that match the following:
        * `action`: The action to perform on the item. Can be `remove` or `approve`.
        * `age_days`: The age of the item in days before the action is performed.
        * `max_reports`: The maximum number of reports before the action is performed.

    - submission:
        Takes action on submissions in the modqueue that match the following:
        * `action`: The action to perform on the item. Can be `remove` or `approve`.
        * `age_days`: The age of the item in days before the action is performed.
        * `max_reports`: The maximum number of reports before the action is performed.
        * `max_comments`: The maximum number of comments before the action is performed.

    - automoderator:
        Takes action on automoderator items in the modqueue that match the following:
            Note these are items that are automatically removed by automoderator.
        * `action`: The action to perform on the item. Can be `remove` or `approve`.
        * `age_days`: The age of the item in days before the action is performed.
        * `max_reports`: The maximum number of reports before the action is performed.
        * `max_comments`: The maximum number of comments before the action is performed.

    - item_notification:
        Sends a notification to a target when an item in the modqueue matches the following:
        * `action`: The action to perform on the item. Can be `notify`.
        * `min_reports`: The minimum number of reports before the action is performed.
        * `target`: The target to send the notification to. Can be `discord:<webhook_url>`.
            The webhook url can be obtained by creating a webhook in a discord channel.

    - user_notification:
        Sends a notification to a target when a user in the modqueue matches the following:
        * `action`: The action to perform on the item. Can be `notify`.
        * `min_reports`: The minimum number of reports before the action is performed.
        * `target`: The target to send the notification to. Can be `discord:<webhook_url>`.
            The webhook url can be obtained by creating a webhook in a discord channel.

Example:
    [remove_unactioned_comments]
    type = "comment"
    details = "bla bla bla"
    action = "remove"
    age_days = 9999
    max_reports = 9999

    [remove_unactioned_submissions]
    type = "submission"
    details = "bla bla bla"
    action = "remove"
    age_days = 9999
    max_reports = 9999
    max_comments = 9999

    [remove_automod_actions]
    type = "automoderator"
    details = "bla bla bla"
    action = "remove"
    age_days = 9999

    [notify_multiple_reports_on_item]
    type = "item_notification"
    details = "bla bla bla"
    action = "notify"
    min_reports = 9999
    target = "discord:https://discordapp.com/api/webhooks/..."

    [notify_multiple_reports_on_user]
    type = "user_notification"
    details = "bla bla bla"
    action = "notify"
    min_reports = 9999
    target = "discord:https://discordapp.com/api/webhooks/..."
"""
logger = botlog("queue_cleaner_plugin")

# Store wiki configuration per subreddit
wiki_config = {}


class QueueCleaner():
    """
    General container for all queue cleaners
    """

    class ActionItem():
        def __init__(self, action, details, item, target=None):
            self.action = action
            self.details = details
            self.item = item
            self.target = target

        def __str__(self) -> str:
            return f"{self.action} {self.item.item_type.permalink} {self.details}"

        def __repr__(self) -> str:
            return str(self)

        def action_do_remove(self):
            self.item.item_type.delete()

        def action_do_approve(self):
            self.item.item_type.approve()

        def action_do_notify(self):
            if self.target.startswith("discord:"):
                webhook_url = self.target[len("discord:"):]
                send_to_discord(webhook_url, f"🚨`{self.details}`\n<{self.item.permalink}>", use_quotes=False)

        def execute(self):
            if self.action == "remove":
                self.action_do_remove()

            elif self.action == "approve":
                self.action_do_approve()

            elif self.action == "notify":
                self.action_do_notify()

    class QueueCleanerBase():
        required_fields = []

        def __init__(self, data):
            # Validate the section
            for field in self.required_fields:
                if field not in data:
                    raise Exception(f"Could not find section {field} in {str(data)}")

            self._data = {}
            for key in data.keys():
                stripped = remove_quotes(str(data[key]).strip())

                # Convert each field to the correct type
                if key not in self.required_fields:
                    raise Exception(f"Unknown field {key} in {str(data)}")

                target_type = self.required_fields[key]

                converted = None
                if hasattr(self, f"init_{key}"):
                    # Handle special inits
                    converted = getattr(self, f"init_{key}")(stripped)
                else:
                    if target_type == bool:
                        converted = stripped.lower() == "true"
                    elif target_type == int:
                        converted = int(stripped)
                    elif target_type == str:
                        converted = str(stripped)
                    elif target_type == datetime.timedelta:
                        converted = datetime.timedelta(days=int(stripped))

                if not converted:
                    raise Exception(f"Could not convert {key} to {target_type}")

                self._data[key] = converted

            self._current_actions = []

        def begin_ingest(self):
            """
            Begin a new ingestion pass
            """
            self._current_actions = []

        def ingest(self, item):
            """
            Ingest a new item
            """
            raise NotImplementedError()

        def end_ingest(self):
            """
            End the current ingestion pass
            """
            actions_copy = self._current_actions.copy()

            self._current_actions = []

            return actions_copy

    class QueueCleanerComment(QueueCleanerBase):
        required_fields = {
            "type": str,
            "details": str,
            "action": str,
            "age_days": datetime.timedelta,
            "max_reports": int,
        }

        def ingest(self, item):
            """
            Ingest a new comment
            """
            queue_item = item.item_type
            if type(queue_item) != comment:
                return

            if item.banned_by != None:
                return

            if queue_item.created_utc_as_datetime > get_utcnow() - self._data["age_days"]:
                return

            if len(queue_item.user_reports) >= self._data["max_reports"]:
                return

            self._current_actions.append(QueueCleaner.ActionItem(
                self._data["action"],
                "[QC-Comment] " + self._data["details"],
                item,
            ))

    class QueueCleanerSubmission(QueueCleanerBase):
        required_fields = {
            "type": str,
            "details": str,
            "action": str,
            "age_days": datetime.timedelta,
            "max_reports": int,
            "max_comments": int,
        }

        def ingest(self, item):
            """
            Ingest a new comment
            """
            queue_item = item.item_type
            if type(queue_item) != submission:
                return

            if queue_item.created_utc_as_datetime > get_utcnow() - self._data["age_days"]:
                return

            if len(queue_item.user_reports) >= self._data["max_reports"]:
                return

            if queue_item.num_comments > self._data["max_comments"]:
                return

            self._current_actions.append(QueueCleaner.ActionItem(
                self._data["action"],
                "[QC-Submission] " + self._data["details"],
                item,
            ))

    class QueueCleanerAutomoderator(QueueCleanerBase):
        required_fields = {
            "type": str,
            "details": str,
            "action": str,
            "age_days": datetime.timedelta,
        }

        def ingest(self, item):
            """
            Ingest a new comment
            """
            queue_item = item.item_type
            if queue_item.created_utc_as_datetime > get_utcnow() - self._data["age_days"]:
                return

            if not item.banned_by or item.banned_by.name != "AutoModerator":
                return

            self._current_actions.append(QueueCleaner.ActionItem(
                self._data["action"],
                "[QC-Automoderator] " + self._data["details"],
                item,
            ))

    class QueueCleanerItemNotification(QueueCleanerBase):
        required_fields = {
            "type": str,
            "details": str,
            "action": str,
            "min_reports": int,
            "target": str,
        }

        def ingest(self, item):
            """
            Ingest a new comment
            """
            queue_item = item.item_type
            if len(queue_item.user_reports) == 0:
                return

            if len(queue_item.user_reports) < self._data["min_reports"]:
                return

            self._current_actions.append(QueueCleaner.ActionItem(
                self._data["action"],
                "[QC-ItemNotification] " + self._data["details"] + f", num reports {len(queue_item.user_reports)}",
                item,
                target=self._data["target"],
            ))

    class QueueCleanerUserNotification(QueueCleanerItemNotification):
        def begin_ingest(self):
            """
            Begin a new ingestion pass
            """
            self._per_user_counters = {}
            self._current_actions = []
            self._author_to_queue_item = {}

        def ingest(self, item):
            """
            Ingest a new item
            """
            if not item.target_author:
                return

            if item.target_author not in self._per_user_counters:
                self._per_user_counters[item.target_author] = 0

            self._author_to_queue_item[item.target_author] = item
            self._per_user_counters[item.target_author] += 1

        def end_ingest(self):
            """
            End the current ingestion pass
            """

            # Check if any users have enough reports
            for user in self._per_user_counters:
                if self._per_user_counters[user] >= self._data["min_reports"]:
                    self._current_actions.append(QueueCleaner.ActionItem(
                        self._data["action"],
                        "[QC-UserNotification] " + self._data["details"]  + f", num reports {self._per_user_counters[user]}",
                        get_user(user),
                        target=self._data["target"],
                    ))

            actions_copy = self._current_actions.copy()
            self._current_actions = []
            return actions_copy

    # What are the required fields inside a section
    required_fields = [
        "type"
    ]

    type_to_class = {
        "comment": QueueCleanerComment,
        "submission": QueueCleanerSubmission,
        "automoderator": QueueCleanerAutomoderator,
        "item_notification": QueueCleanerItemNotification,
        "user_notification": QueueCleanerUserNotification,
    }

    def __init__(self) -> None:
        self._configs = {}

    def add_config(self, data, name):
        # Validate the section
        for field in self.required_fields:
            if field not in data:
                raise Exception(f"Could not find section {field} in {str(data)}")

        item_type = remove_quotes(data["type"])
        if item_type not in self.type_to_class:
            raise Exception(f"No such action type {item_type} in {str(data)}")

        self._configs[name] = self.type_to_class[item_type](data)

    def begin_ingest(self):
        """
        Begin a new ingestion pass
        """
        for config in self._configs.values():
            config.begin_ingest()

    def ingest(self, item):
        """
        Ingest a new item for all configurations
        """
        for config in self._configs.values():
            config.ingest(item)

    def end_ingest(self):
        """
        End the current ingestion pass and process all actions
        """
        action_list = []
        for config in self._configs.values():
            action_list.append(config.end_ingest())

        # Concatenate all actions
        actions_per_item = {}
        for actions in action_list:
            for action in actions:
                item_id = action.item.permalink
                if item_id not in actions_per_item:
                    actions_per_item[item_id] = []
                actions_per_item[item_id].append(action)

        if len(actions_per_item) != 0:
            message = ""
            for item_id, actions in actions_per_item.items():
                message += f"Item {item_id}:\n"
                for action in actions:
                    message += f"    {action.action}: {action.details}\n"

            logger.debug(f"Got actions:\n{message}")

        # Check if there are conflicting actions
        # i.e. remove & approve
        conflicts = set(["approve", "remove"])
        for item_id, actions in actions_per_item.copy().items():
            actions_set = set()
            for action_data in actions:
                actions_set.add(action_data.action)

            if actions_set.issuperset(conflicts):
                logger.error(
                    f"Conflicting actions approve/remove found for item {item_id}: str({actions_set})\nSkipping...")

                # Remove the item from the list
                del actions_per_item[item_id]

        # Execute the actions
        for item_id, actions in actions_per_item.items():
            for action in actions:
                action.execute()


def wiki_changed(sub, change):
    logger.debug("Wiki changed for log_actions, subreddit %s" % sub)
    cont = parse_wiki_content(change.content)

    if not cont:
        change.author.send_pm(
            "Error parsing the updated wiki page on %s" % sub)
        return

    config = QueueCleaner()
    try:
        # Read each section
        for section in cont:
            if section == "DEFAULT":
                continue

            # Add it to config
            config.add_config(cont[section], section)
    except Exception as e:
        change.author.send_pm(
            "Error parsing the updated wiki page on %s" % sub, str(e))

    # Save the config
    wiki_config[sub.display_name] = config
    logger.debug("Added config to wiki_config. Current list: %s" %
                 str(wiki_config.keys()))


wiki = hook.register_wiki_page(
    wiki_page="queue_cleaner",
    description="Clean the modqueue in given conditions",
    documentation=plugin_documentation,
    wiki_change_notifier=wiki_changed)

def do_scrape_modqueue(config, subreddit_name):
    """
    Scrape the modqueue for a subreddit
    """
    # Start the scraper
    config.begin_ingest()

    for item in scrape_modqueue(subreddit_name):
        # Ingest the item
        config.ingest(item)

    # End the scraper
    config.end_ingest()

# @hook.on_start(wiki=wiki)
# def startup_scraper(subreddit):
#     if subreddit.display_name not in wiki_config:
#         return

#     do_scrape_modqueue(
#         wiki_config[subreddit.display_name],
#         subreddit.display_name)

# Do this every 5 minutes
@hook.periodic(period=300)
def scrapeit():
    for subreddit_name in wiki_config:
        do_scrape_modqueue(
            wiki_config[subreddit_name],
            subreddit_name)