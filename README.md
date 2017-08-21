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

