import asyncio
from typing import List
from shmchannel import MODE_SERVER, MODE_CLIENT, Channel

mode = None


def notification_received(data: bytes):
    print("%s: Notification received: %s" % (mode, data.decode()))


async def _request_received(data: bytes) -> bytes:
    for i in range(5, 0, -1):
        print("%s: Request received: %s ... %d" % (mode, data.decode(), i))
        await asyncio.sleep(1)
    return data


async def main(args: List[str]) -> int:
    global mode
    if len(args) == 3:
        mode = MODE_SERVER if args[1] == "server" else MODE_CLIENT
        message = args[2]
        channel = Channel("/test", mode)
        channel.set_notification_callback(notification_received)
        channel.set_request_callback(_request_received)
        channel.open()

        task = asyncio.ensure_future(channel.send_receive())
        channel.notify(message.encode())
        print("Request sent:", message)
        data = await channel.request(message.encode())
        print("%s: Response received: %s" % (mode, data.decode()))
        await task
        channel.close()
        return 0
    else:
        print("Usage: %s server|client message" % args[0])
        return 1

if __name__ == "__main__":
    import sys
    loop = asyncio.get_event_loop()
    sys.exit(loop.run_until_complete(main(sys.argv) or 0))
