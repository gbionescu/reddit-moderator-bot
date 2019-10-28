import logging
import os

LOGS_FOLDER = "logs/"
CONSOLIDATED_LOGS = "logs/bot/"
logs = {}

def botlog(name, console=logging.INFO, file=logging.DEBUG):
    if name in logs:
        return logs[name]

    # Create logs folder
    os.makedirs(LOGS_FOLDER, exist_ok=True)
    os.makedirs(CONSOLIDATED_LOGS, exist_ok=True)

    logger = logging.getLogger(name)
    logger.setLevel(logging.DEBUG)

    ch = logging.StreamHandler()
    ch.setLevel(console)

    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    ch.setFormatter(formatter)

    fh1 = logging.FileHandler(CONSOLIDATED_LOGS + "bot.log")
    fh1.setLevel(file)
    fh1.setFormatter(formatter)

    fh2 = logging.FileHandler("%s/%s.log" % (LOGS_FOLDER, name))
    fh2.setLevel(file)
    fh2.setFormatter(formatter)

    logger.addHandler(ch)
    logger.addHandler(fh1)
    logger.addHandler(fh2)

    logs[name] = logger
    return logger