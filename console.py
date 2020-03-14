import grpc

from tools.botrpc import console_pb2, console_pb2_grpc

channel = grpc.insecure_channel('localhost:5151')
stub = console_pb2_grpc.BotStub(channel)

idx = 0
try:
    while True:
        res = stub.toBot(console_pb2.request(data="asd" + str(idx)))
        print(res)
        idx += 1
        import time
        time.sleep(1)
except:
    import traceback
    traceback.print_exc()