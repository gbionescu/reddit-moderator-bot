import logging
logs = {}

def botlog(name, console=logging.DEBUG, file=logging.DEBUG):
    if name in logs:
        return logs[name]

    logger = logging.getLogger(name)
    logger.setLevel(logging.DEBUG)

    ch = logging.StreamHandler()
    ch.setLevel(console)

    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    ch.setFormatter(formatter)

    fh = logging.FileHandler("bot.log")
    fh.setLevel(file)
    fh.setFormatter(formatter)

    logger.addHandler(ch)
    logger.addHandler(fh)

    logs[name] = logger
    return logger