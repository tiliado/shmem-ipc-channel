Shared Memory & IPC Channel
===========================

This project contains a wrapper object to work with shared memory
and an implementation of IPC channel based on that.

Basic Info
----------

  - **Author:** Jiří Janoušek
  - **License:** [BSD-2-Clause](./LICENSE)
  - **Supported platforms:** Unix with POSIX shared memory and POSIX semaphores.
  - **Documentation:** See [lib/doc](./lib/doc)
  - **Examples:** See [lib/examples](./lib/examples)
  - **Test suite:** TODO
  - **Status:** ABI-unstable

Vala/C Library
--------------

### Dependencies

  - GNU Make
  - Python 3
  - Valac
  - g-ir-compiler
  - glib-2.0 and friends (and respective GIR XML files)

### Build

```bash
./configure
make all
```

Python 3 Module
---------------

### Dependencies

  - cffi
  - Python 3.6
