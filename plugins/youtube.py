import re

from dataclasses import dataclass
from types import new_class

from modbot import hook
from modbot.log import botlog
from modbot.utils import parse_wiki_content
import modbot.ytaccess as yt

plugin_documentation = r"""
Take actions when youtube channels are posted.

Configurable parameters are:
- id - channel ID to watch - make sure that it's an ID and not the channel name. To get the channel ID, right click on the channel page -> view source and search for 'channelID'.
- message - what message to send.
- report - what report to send.
- delete - whether to delete the post. Cannot be specified when 'report' is set. Defaults to 'False'. When set to 'True', the 'message' field needs to be set.

The message and report field are optional, but one of them needs to be specified. It's also possible to specify both.

The message can be formatted with:
    ${AUTHOR} - author name
    ${KIND} - submission / comment

Example configuration:
[some_channel]
id = 123456
message = got a post by some channel
report = reports are optional

[some_other_channel]
id = ABCDEFG
message = blah

[another_channel]
id = ABCDEFG
delete = True
"""

logger = botlog("yt")

# Store wiki configuration per subreddit
wiki_config = {}

# Taken from: https://stackoverflow.com/questions/19377262/regex-for-youtube-url
yt_validator = re.compile(r"^((?:https?:)?\/\/)?((?:www|m)\.)?((?:youtube\.com|youtu.be))(\/(?:[\w\-]+\?v=|embed\/|v\/)?)([\w\-]+)(\S+)?$")


class PluginCfg():
    @dataclass
    class YTConfig:
        """Keeps config for a youtube channel."""
        ytid: str
        message: str = None
        report: str = None
        delete: bool = False

    def __init__(self, content, author):
        # Mark that a configuration is valid
        self.sections = []

        # Parse all sections
        for section_name in content.sections():
            logger.debug(f"Found section {section_name}")

            # Validate that ID is set
            section = content[section_name]
            if not section.get("id", None):
                logger.error("Invalid section. Does not contain id.")
                continue

            message = section.get("message", None)
            report = section.get("report", None)
            delete = section.get("delete", False)

            if not message and not report:
                logger.error(f"Invalid section {section_name}: does not contain message or report.")
                author.send_pm("YT plugin error", f"Invalid section {section_name}: does not contain message or report.")
                continue

            if report and delete:
                logger.error(f"Invalid section {section_name}: both report and delete found.")
                author.send_pm("YT plugin error", f"Invalid section {section_name}: both report and delete found.")
                continue

            if delete and not message:
                logger.error(f"Invalid section {section_name}: delete found but message not found.")
                author.send_pm("YT plugin error", f"Invalid section {section_name}: delete found but message not found.")
                continue

            new_config = PluginCfg.YTConfig(section.get("id"), message, report, delete)
            self.sections.append(new_config)
            logger.debug(f"Added {new_config}")


def wiki_changed(sub, change):
    logger.debug("Wiki changed for yt, subreddit %s" % sub)
    cont = parse_wiki_content(change.content)

    wiki_config[sub.display_name] = PluginCfg(cont, change.author)


wiki = hook.register_wiki_page(
    wiki_page="youtube",
    description="Send notifications on youtube channel posts.",
    documentation=plugin_documentation,
    wiki_change_notifier=wiki_changed)

def format_message(message, submission=None, comment=None):
    if submission:
        message = message.replace(r"${AUTHOR}", submission.author.name)
        message = message.replace(r"${KIND}", "submission")
        message = message.replace(r"${LINK}", submission.shortlink)
    elif comment:
        message = message.replace(r"${AUTHOR}", comment.author)
        message = message.replace(r"${KIND}", "comment")
        message = message.replace(r"${LINK}", comment.url)

    return message

@hook.submission(wiki=wiki)
def new_yt_post(submission, reddit, subreddit):
    # Match the submission URL with the validator
    match = yt_validator.match(submission.url)

    if not match:
        return

    # Group 3 is the domain
    if match.group(3) not in ["youtube.com", "yout.be"]:
        return

    chan_id = yt.get_channel_id(match.group(5))

    if subreddit.display_name not in wiki_config:
        logger.error("Subreddit config not found.")
        return
    logger.info(f"New YT post by {submission.author.name} - {submission.url}")

    for cfg in wiki_config[subreddit.display_name].sections:
        # Look for the matching channel ID
        if cfg.ytid == chan_id:
            if cfg.message:
                logger.info("Sent modmail.")
                subreddit.send_modmail("YouTube channel event", format_message(cfg.message, submission))

            if cfg.delete:
                logger.info("Deleted post.")
                submission.delete(spam=True)

            if cfg.report:
                logger.info("Report sent.")
                submission.report(format_message(cfg.report, submission))
