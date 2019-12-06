import os
import json
import collections
import logging
import platform
import shutil
from shutil import copyfile
from oslo_concurrency import lockutils

logger = logging.getLogger("storage")
logger.setLevel(logging.DEBUG)
fh = logging.FileHandler("storage.log")
fh.setLevel(logging.DEBUG)
logger.addHandler(fh)

DS_LOC = "storage_data/"

class dstype():
    def __init__(self, parent, name):
        if not name.endswith(".json"):
            name = name + ".json"

        logger.debug("Initializing %s, %s" % (parent, name))

        os.makedirs(os.path.join(DS_LOC, parent, "backup"), exist_ok=True)

        self.location = parent + "/" + name
        self.backup_name = parent + "/backup/" + name

        data_obj = self.get_obj(self.location)
        if data_obj:
            self.data = data_obj

    def sync(self):
        do_sync(self.data, self.location, self.backup_name)

    def get_obj(self, location):
        try:
            if platform.system() == "Windows":
                logger.info("Load file %s windows" % location)
                data = json.load(open(self.get_win_path(DS_LOC + location), "r"))
            else:
                logger.info("Load file %s linux" % location)
                data = json.load(open(DS_LOC + location, "r"))
            return data
        except:
            logger.error("Trying backup %s" % location)
            try:
                # Try the backup
                if platform.system() == "Windows":
                    data = json.load(open(self.get_win_path( DS_LOC + self.backup_name), "r"))
                else:
                    data = json.load(open(DS_LOC + self.backup_name, "r"))

                logger.critical("Loaded backup for " + self.location)
                return data
            except:
                logger.error("Could not load " + self.location)
                return None

class dsobj(dstype, collections.UserDict):
    def __init__(self, parent, name):
        self._data = dsdict(parent, name)

    def __getattr__(self, name):
        if not name.startswith("_"):
            try:
                return self._data[name]
            except KeyError:
                # Handle hasattr
                raise AttributeError
        else:
            return super().__getattribute__(name)

    def __setattr__(self, name, value):
        if name.startswith("_"):
            super().__setattr__(name, value)
        else:
            self._data[name] = value

class dsdict(dstype, collections.UserDict):
    def __init__(self, parent, name):
        collections.UserDict.__init__(self)
        dstype.__init__(self, parent, name)

    def __getitem__(self, key):
        return collections.UserDict.__getitem__(self, key)

    def __setitem__(self, key, value):
        collections.UserDict.__setitem__(self, key, value)
        self.sync()
        return self.data

def do_sync(obj, name, backup_name):
    @lockutils.synchronized(name)
    def do_blocking_sync(obj, name, backup_name):
        try:
            logger.debug("Do sync on " + name)

            # Check if the current file is valid
            json.load(open(DS_LOC + name, "r"))

            # If yes, do a backup
            shutil.copy(DS_LOC + name, DS_LOC + backup_name)

            logger.debug("Load/sync OK")
        except FileNotFoundError:
            pass
        except:
            print("Sync error when syncing %s" % name)
            logger.debug("Sync error when syncing %s" % name)
            import traceback; traceback.print_exc()

        logger.debug("Open file")

        out = json.dumps(obj, indent=4, sort_keys=True)
        file = open(DS_LOC + name, "w")
        file.write(out)
        file.close()

        logger.debug("Sync finished")

    do_blocking_sync(obj, name, backup_name)