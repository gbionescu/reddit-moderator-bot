import grpc
from concurrent import futures
from tools.botrpc import console_pb2, console_pb2_grpc

class rpcuser():
    def __init__(self):
        self.username = "console_user"

    def __repr__(self):
        return self.username

    def send_pm(self, subject, text, skip_signature=False):
        print(subject)
        print(text)

    @property
    def name(self):
        return self.username


class rpcmessage():
    """
    Encapsulate an inbox message
    """

    def __init__(self, body):
        self.body = body
        self.author = rpcuser()

class Servicer(console_pb2_grpc.BotServicer):
    def __init__(self, callback):
        self.callback = callback

    def toBot(self, request, context):
        self.callback(rpcmessage(request.data))

        return console_pb2.response(data="res")

def create_server(inbox_func):
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    console_pb2_grpc.add_BotServicer_to_server(Servicer(inbox_func), server)

    server.add_insecure_port("localhost:5151")
    server.start()

    return server