import asyncio
from typing import List

from libshmch import MODE_SERVER, MODE_CLIENT
from shmchannel import libshmch

Role = int


class Channel:
    def __init__(self, name: str, role: Role):
        self._name = name
        self._role = role
        self._channel = libshmch.channel_new(name, role)
        self._request_callback = None
        libshmch.channel_set_request_callback(self._channel, self._process_request)

    def destroy(self):
        if self._channel:
            libshmch.channel_unref(self._channel)
            self._channel = None

    @property
    def name(self) -> str:
        return self._name

    @property
    def role(self) -> Role:
        return self._role

    def open(self):
        libshmch.channel_open(self._channel)

    def close(self):
        return libshmch.channel_close(self._channel)

    async def request(self, data: bytes) -> bytes:
        future = asyncio.Future()
        libshmch.channel_request(self._channel, data, future.set_result)
        return await future

    def notify(self, data: bytes):
        libshmch.channel_notify(self._channel, data)

    def set_notification_callback(self, callback):
        libshmch.channel_set_notification_callback(self._channel, callback)

    def set_request_callback(self, callback):
        self._request_callback = callback

    def _process_request(self, data: bytes, respond):
        if self._request_callback:
            def done_callback(future):
                respond(future.result())

            task = asyncio.ensure_future(self._request_callback(data))
            task.add_done_callback(done_callback)
        else:
            respond(data)

    async def send_receive(self):
        while True:
            libshmch.channel_send_receive(self._channel, False)
            await asyncio.sleep(0.001)


if __name__ == "__main__":
    _mode = None

    def _notification_received(data: bytes):
        print("%s: Notification received: %s" % (_mode, data.decode()))

    async def _request_received(data: bytes) -> bytes:
        for i in reversed(range(5)):
            print("%s: Request received: %s ... %d" % (_mode, data.decode(), i))
            await asyncio.sleep(1)

        return data


    async def _main(args: List[str]) -> int:
        global _mode
        if len(args) == 3:
            _mode = MODE_SERVER if args[1] == "server" else MODE_CLIENT
            message = args[2]
            channel = Channel("/test", _mode)
            channel.set_notification_callback(_notification_received)
            channel.set_request_callback(_request_received)
            channel.open()

            task = asyncio.ensure_future(channel.send_receive())
            channel.notify(message.encode())
            data = await channel.request(message.encode())
            print("%s: Response received: %s" % (_mode, data.decode()))
            await task
            channel.close()
        return 0

    import sys
    _loop = asyncio.get_event_loop()
    _main.running = True
    code = _loop.run_until_complete(_main(sys.argv))
    sys.exit(code or 0)
