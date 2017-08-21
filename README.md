Shared Memory & IPC Channel
===========================

This project contains a wrapper object to work with shared memory
and an implementation of IPC channel based on that.

Basic Info
----------

  - **Author:** Jiří Janoušek
  - **License:** [BSD-2-Clause](./LICENSE)
  - **Supported Runtimes:** Vala/C, Python 3.6/asyncio
  - **Supported Platforms:** Unix with POSIX shared memory and POSIX semaphores.
  - **Documentation:** Vala → [lib/doc](./lib/doc), Python → TODO. 
  - **Examples:** See examples section bellow or [./examples](./examples)
  - **Test Suite:** TODO
  - **Status:** Early alpha, ABI-unstable

Examples
--------

### Vala

  - Source: [examples/vala/channel.vala](./examples/vala/channel.vala)
  - Run as: `./channel server "Message from server."` and
    `./channel client "Message from client."`

```vala
Shmch.Mode role;

void response_received(uint8[] data) {
    stdout.printf("%s: Response received: %s\n", role.to_string(), (string) data);
}

void notification_received(uint8[] data) {
    stdout.printf("%s: Notification received: %s\n", role.to_string(), (string) data);
}

void request_received(Shmch.IncomingRequest request) {
    stdout.printf("%s: Request received: %s\n", role.to_string(), (string) request.get_data());
    request.send_response(request.get_data());
}

int main(string[] args) {
    if (args.length == 3) {
        role = args[1] == "server" ? Shmch.Mode.SERVER : Shmch.Mode.CLIENT;
        var message = args[2];
        var channel = new Shmch.Channel("/test", role);
        channel.set_notification_callback(notification_received);
        channel.set_request_callback(request_received);
        channel.open();
        channel.request(message.data, response_received);
        stdout.printf("Request sent: %s\n", message);
        channel.notify(message.data);
        while (true) {
            channel.send_receive(true);
            Thread.usleep(100000);
        }
        channel.close();
        return 0;
    } else {
        stderr.printf("Usage: %s server|client message\n", args[0]);
        return 1;
    }
}
```
### Python/asyncio

- Source: [examples/python/channel.py](./examples/python/channel.py)
- Run as: `python3.6 examples/python/channel.py server "Message from server."` and
    `python3.6 examples/python/channel.py client "Message from client."`
    
```python
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
```

### Mixed

  - **Vala server:** `./channel server "Message from server."`:

```
Request sent: Message from server.
SHMCH_MODE_SERVER: Notification received: Message from client.
SHMCH_MODE_SERVER: Request received: Message from client.
SHMCH_MODE_SERVER: Response received: Message from server.
```

  - **Python client:** `python3.6 examples/python/channel.py client "Message from client."`:

```
Request sent: Message from client.
1: Notification received: Message from server.
1: Request received: Message from server. ... 5
1: Response received: Message from client.
1: Request received: Message from server. ... 4
1: Request received: Message from server. ... 3
1: Request received: Message from server. ... 2
1: Request received: Message from server. ... 1
```


Dependencies
-----------

  - **Vala/C Library:**
      - GNU Make
      - Python 3
      - Valac
      - g-ir-compiler
      - glib-2.0 and friends (and respective GIR XML files)
  - **Python Bindings:**
      - Python 3.6
      - setuptools
      - cffi

Build Instructions
------------------

```bash
./configure --help
./configure ...
make all
make install
make DESTDIR=... install
```

