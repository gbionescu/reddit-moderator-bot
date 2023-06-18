import logging
import os
import enum
from logging.handlers import RotatingFileHandler

MAX_LOG_SIZE = 1024 * 1024 * 100
LOGS_FOLDER = "logs/"
logs = {}

# Map of discord webhooks
discord_wh = {}


@enum.unique
class loglevel(enum.Enum):
    INFO = 0
    DEBUG = 1
    ERROR = 2


# Map corresponding logging levels
logmap = {
    loglevel.INFO: logging.INFO,
    loglevel.DEBUG: logging.DEBUG,
    loglevel.ERROR: logging.ERROR}


def send_to_discord(webhook_url, message, use_quotes=True):
    """
    Sends a message to a discord webhook
    """
    from discord_webhook import DiscordWebhook

    def quote_message(message):
        if len(message) == 0:
            return ""
        return f"```-\n{message}```"

    chunk_size = 2000 - len("```-\n```")

    while len(message) != 0:
        quoted = None
        if use_quotes:
            quoted = quote_message(message[:chunk_size])
        else:
            quoted = message[:chunk_size]

        webhook = DiscordWebhook(webhook_url, content=quoted)
        webhook.execute()
        message = message[chunk_size:]

class discord_handler(logging.Handler):
    def send_message(self, record, url):
        # TODO: Disabled embeds
        # If not a multiline error, add embeds
        # if "\n" not in record.message:
        #     webhook = DiscordWebhook(url)
        #     embed = DiscordEmbed()
        #     embed.add_embed_field(
        #         name='File', value=record.filename, inline=True)
        #     embed.add_embed_field(
        #         name='Level', value=record.levelname, inline=True)
        #     embed.add_embed_field(
        #         name='Message', value=record.message, inline=True)

        #     # add embed object to webhook
        #     webhook.add_embed(embed)
        # else:
        message = f"[{record.levelname}] {record.message}"

        send_to_discord(url, message)

    def emit(self, record):
        if self.name in discord_wh:
            self.send_message(record, discord_wh[self.name])


def add_discord_webhook(name, url):
    """
    Add a discord webhook to the webhook list
    """
    discord_wh[name] = url


def botlog(name, console_level=loglevel.INFO, file_level=loglevel.DEBUG):
    """
    Simple wrapper around the logger object
    """
    if name in logs:
        return logs[name]

    if console_level not in logmap:
        raise ValueError("Invalid console logging level provided")

    if file_level not in logmap:
        raise ValueError("Invalid file logging level provided")

    logging_console = logmap[console_level]
    logging_file = logmap[file_level]

    # Create logs folder
    os.makedirs(LOGS_FOLDER, exist_ok=True)

    logger = logging.getLogger(name)
    logger.setLevel(logging.DEBUG)

    ch = logging.StreamHandler()
    ch.setLevel(logging_console)

    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    ch.setFormatter(formatter)

    fh = RotatingFileHandler("%s/%s.log" % (LOGS_FOLDER, name), maxBytes=MAX_LOG_SIZE, backupCount=2)
    fh.setLevel(logging_file)
    fh.setFormatter(formatter)

    logger.addHandler(ch)
    logger.addHandler(fh)

    # Create discord handler with the same level as for file
    discord_stream = discord_handler()
    discord_stream.set_name(name)
    discord_stream.setLevel(logging_file)
    discord_stream.setFormatter(formatter)
    logger.addHandler(discord_stream)

    logs[name] = logger
    return logger
