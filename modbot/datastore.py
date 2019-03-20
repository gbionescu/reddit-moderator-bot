import os
import pickle

DS_LOC = "data/"
os.system("mkdir -p %s" % DS_LOC)

class dslist():
    def __init__(self, name):
        if get_obj(name) is not None:
            self.data = get_obj(name)
        else:
            self.data = []

        self.name= name

        do_sync(self, name)

    def __repr__(self):
        return self.data

    def __str__(self):
        return str(self.data)

    def __len__(self):
        return len(self.data)

    def sync(self):
        do_sync(self, self.name)

    def __getitem__(self, key):
        return self.data[key]

    def __setitem__(self, key, value):
        self.data[key] = value
        self.sync()
        return self.data

    def append(self, item):
        self.data.append(item)
        self.sync()
        return self.data

    def extend(self, ex_list):
        self.data.extend(ex_list)
        self.sync()
        return self.data

    def remove(self, item):
        self.data.remove(item)
        self.sync()
        return self.data

def do_sync(obj, name):
    dso = open(DS_LOC + name + ".data", "wb")
    dso.write(pickle.dumps(obj))
    dso.close()

def get_obj(name):
    try:
        data = pickle.load(open(DS_LOC + name + ".data", "rb"))
        return data
    except:
        return None
