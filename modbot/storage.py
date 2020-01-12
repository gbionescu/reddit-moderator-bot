import os
import json
import collections
import platform
import shutil
from modbot.log import botlog, loglevel
from shutil import copyfile
from oslo_concurrency import lockutils

logger = botlog(
    "storage.log",
    console_level=loglevel.ERROR,
    file_level=loglevel.ERROR)

DS_LOC = "storage_data/"

class dstype():
    def __init__(self, parent, name):
        if not name.endswith(".json"):
            name = name + ".json"

        parent = DS_LOC + parent
        logger.debug("Initializing %s, %s" % (parent, name))

        os.makedirs(os.path.join(parent, "backup"), exist_ok=True)

        self.location = parent + "/" + name
        self.backup_name = parent + "/backup/" + name

        data_obj = self.get_obj(self.location)
        if data_obj:
            self.data = data_obj

    def sync(self):
        do_sync(self.data, self.location, self.backup_name)

    def get_obj(self, location):
        try:
            if os.path.isfile(location):
                logger.info("Load file %s linux" % location)
                data = json.load(open(location, "r"))
                return data
            elif os.path.isfile(self.backup_name):
                logger.error("Trying backup %s" % (self.backup_name))
                # Try the backup
                data = json.load(open(self.backup_name, "r"))
                logger.critical("Loaded backup for " + self.location)
                return data
        except:
            try:
                if os.path.isfile(self.backup_name):
                    logger.error("Trying backup %s" % (self.backup_name))
                    # Try the backup
                    data = json.load(open(self.backup_name, "r"))
                    logger.critical("Loaded backup for " + self.location)
                    return data
            except:
                return None
            logger.error("Could not load " + self.location)
            return None

class dsobj():
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
            if os.path.isfile(name):
                logger.debug("Do sync on " + name)

                # Check if the current file is valid
                json.load(open(name, "r"))

                # If yes, do a backup
                shutil.copy(name, backup_name)

                logger.debug("Load/sync OK")
        except FileNotFoundError:
            pass
        except:
            print("Sync error when syncing %s" % name)
            logger.debug("Sync error when syncing %s" % name)
            import traceback; traceback.print_exc()

        logger.debug("Open file")

        out = json.dumps(obj, indent=4, sort_keys=True)
        file = open(name, "w")
        file.write(out)
        file.close()

        logger.debug("Sync finished")

    do_blocking_sync(obj, name, backup_name)

def set_storage_loc(location):
    global DS_LOC
    DS_LOC = location

def clean_storage_loc(location):
    import shutil

    try:
        shutil.rmtree(location)
    except:
        pass