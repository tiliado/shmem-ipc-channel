import os
import sys
from cffi import FFI

directory = os.path.abspath(os.path.dirname(__file__))
root = os.path.dirname(directory)
build = os.path.join(root, "build")

if root not in sys.path:
    sys.path.insert(0, root)

from buildconfig import pkg, LDFLAGS, extract_include_dirs
pkg("glib-2.0")

with open(os.path.join(directory, "shmch.c")) as fh:
    source = fh.read()
with open(os.path.join(directory, "shmch.h")) as fh:
    header = fh.read()

builder = FFI()
builder.set_source(
    "libshmch_cffi",
    source,
    libraries=["shmchannel"],
    include_dirs=[build] + extract_include_dirs(),
    library_dirs=[build],
    extra_link_args=LDFLAGS,
    extra_compile_args=[])

builder.cdef(header)

if __name__ == "__main__":
    builder.compile(tmpdir=os.path.join(build, "cffi"), verbose=True)
