import os
import json
import collections
import logging
import platform
from shutil import copyfile

logger = logging.getLogger("storage")
logger.setLevel(logging.DEBUG)
fh = logging.FileHandler("storage.log")
fh.setLevel(logging.DEBUG)
logger.addHandler(fh)

DS_LOC = "storage_data/"

class dstype():
    def __init__(self, parent, name):
        logger.debug("Initializing %s, %s" % (parent, name))

        os.makedirs(os.path.join(DS_LOC, parent, "backup"), exist_ok=True)

        self.location = parent + "/" + name
        self.backup_name = parent + "/backup/" + name

        data_obj = self.get_obj(self.location)
        if data_obj:
            self.data = data_obj

    def do_sync(self, obj, name, backup_name):
        try:
            logger.debug("Do sync on " + name)

            # Check if the current file is valid
            json.load(open(DS_LOC + name, "r"))

            # If yes, do a backup
            shutil.copy(DS_LOC + name, DS_LOC + backup_name)

            logger.debug("Load/sync OK")
        except:
            print("File at %s is not valid" % (DS_LOC + name))
            logger.debug("Sync error - file invalid")

        logger.debug("Open file")
        file = open(DS_LOC + name, "w")

        json.dump(obj, file, indent=4, sort_keys=True)
        logger.debug("Sync finished")

    def sync(self):
        return
        self.do_sync(self.data, self.location, self.backup_name)

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

class dsdict(dstype, collections.UserDict):
    def __init__(self, parent, name):
        collections.UserDict.__init__(self)
        dstype.__init__(self, parent, name)

    def __getitem__(self, key):
        try:
            return collections.UserDict.__getitem__(self, key)
        except:
            return None

    def __setitem__(self, key, value):
        collections.UserDict.__setitem__(self, key, value)
        self.sync()
        return self.data
