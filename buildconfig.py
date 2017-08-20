#!/usr/bin/env python3.6
import shlex
import subprocess as _subprocess

CFLAGS = []
LDFLAGS = []
VALAFLAGS = []
VARIABLES = []


def cflags(flags):
    CFLAGS.append(flags)


def ldflags(flags):
    LDFLAGS.append(flags)


def valaflags(flags):
    VALAFLAGS.append(flags)


def stdout(*args) -> str:
    return _subprocess.run(*args, stdout=_subprocess.PIPE, check=True).stdout.decode("utf-8")


def pkg_version(mod: str, parts: int = 0) -> str:
    version = stdout(["pkg-config", "--modversion", mod]).strip()
    return ".".join(version.split(".")[0:parts]) if parts else version


def pkg(mod: str):
    for mod in mod.split():
        CFLAGS.append(stdout(["pkg-config", "--cflags", mod]).strip())
        LDFLAGS.append(stdout(["pkg-config", "--libs", mod]).strip())


def var(definition, *args):
    if args:
        definition = definition % args
    VARIABLES.append(definition + "\n")


def project(name, version):
    var("PROJECT := %s", name)
    var("VERSION := %s", version)


def _add_builtin():
    for name, item in globals().items():
        if not name.startswith("_"):
            __builtins__[name] = item
            # setattr(__builtins__, name, item)


def extract_include_dirs():
    return [flag[2:] for flag in shlex.split(" ".join(CFLAGS)) if flag.startswith("-I")]


def finish():
    with open("config.mk", "wt") as f:
        var("CFLAGS := %s $(CFLAGS)", " ".join(CFLAGS))
        var("LDFLAGS := %s $(LDFLAGS)", " ".join(LDFLAGS))
        var("VALAFLAGS := %s $(addprefix -X , $(CFLAGS) $(LDFLAGS)) $(VALAFLAGS)", " ".join(VALAFLAGS))
        f.write("".join(VARIABLES))

    with open("config.mk") as f:
        print(f.read())
