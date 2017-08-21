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
  - **Documentation:** See [lib/doc](./lib/doc)
  - **Examples:** See [lib/examples](./lib/examples)
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

