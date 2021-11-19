import threading
import sys
import time
from os.path import dirname as d
from os.path import abspath, join
from modbot.storage import dsdict

import pytest


def test_stor():
    to_wait = []

    def do_test(obj, cycles):
        for i in range(cycles):
            print("Cycle %d", i)
            if "test" not in obj:
                obj["test"] = []

            obj["test"].append(i)
            obj.sync()

    def launch_threads(fname, nb_threads, cycles):
        test_dict = dsdict("test", fname)
        nb_threads = nb_threads
        for thr in range(nb_threads):
            print("Launching thread %d", thr)
            test_th = threading.Thread(
                name="pmgr_thread",
                target=do_test,
                args=(test_dict, cycles))

            to_wait.append(test_th)

    launch_threads("test", 50, 10)
    launch_threads("test2", 50, 10)

    while True:
        keep_going = False
        for thr in to_wait:
            if thr.is_alive():
                keep_going = True

        if not keep_going:
            break
        time.sleep(0.1)
