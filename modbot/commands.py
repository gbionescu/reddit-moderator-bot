
cmd_list = {}
cmd_prefix = "/"

class command():
    def __init__(self, func, name, documentation, requested_args, avail_args):
        self.func = func
        self.name = name
        self.doc = documentation
        self.requested_args = requested_args
        self.avail_args = avail_args

        if self.name not in cmd_list:
            cmd_list[self.name] = self
        else:
            print("Command %s already registered, ignoring" % self.name)

def set_prefix(prefix):
    global cmd_prefix
    cmd_prefix = prefix

def get_cmd_list():
    for cmd in cmd_list.keys():
        yield cmd

def execute_command(name):
    pass

def execute_matching_cmd(cmd):
    if len(cmd) == 0 or cmd[0] != cmd_prefix:
        return None

    cmd = cmd[1:]

    if cmd in cmd_list:
        cmd_list[cmd].func()