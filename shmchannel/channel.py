import asyncio

from shmchannel import libshmch

MODE_SERVER, MODE_CLIENT = libshmch.MODE_SERVER, libshmch.MODE_CLIENT
Mode = int


class Channel:
    def __init__(self, name: str, role: Mode):
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
    def role(self) -> Mode:
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
