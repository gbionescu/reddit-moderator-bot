import psutil
import os
import time
from datetime import timedelta
from modbot import hook

@hook.command(permission=hook.permission.OWNER)
def system_status(message):
    """
    Prints information about the system status
    """
    process = psutil.Process(os.getpid())

    # get the data we need using the Process we got
    cpu_usage = process.cpu_percent(1)
    thread_count = process.num_threads()
    memory_usage = process.memory_info()[0] / (1024 * 1024)
    uptime = timedelta(seconds=round(time.time() - process.create_time()))

    reply = \
    """
    Uptime: %s
    Threads: %s
    CPU Usage: %s
    Memory Usage (MB): %s""" % (
        uptime,
        thread_count,
        cpu_usage,
        memory_usage
    )

    message.author.send_pm("System status", reply)