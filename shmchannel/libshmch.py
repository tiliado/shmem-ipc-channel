from contextlib import contextmanager
from typing import Any, Callable

try:
    # noinspection PyUnresolvedReferences
    from shmchannel.libshmch_cffi import ffi, lib
except ImportError:
    # noinspection PyUnresolvedReferences
    from build.cffi.libshmch_cffi import ffi, lib

MODE_CLIENT = lib.SHMCH_MODE_CLIENT
MODE_SERVER = lib.SHMCH_MODE_SERVER
Ptr = Any
_handles = set()


@ffi.def_extern()
def destroy_notify(handle):
    _handles.discard(handle)


def wrap_user_data(item):
    h = ffi.new_handle(item)
    _handles.add(h)
    return h, lib.destroy_notify


@ffi.def_extern()
def data_callback(data, size, user_data):
    func = ffi.from_handle(user_data)
    func(bytes(ffi.buffer(data, size)))


def wrap_data_callback(func):
    handle, destroy = wrap_user_data(func)
    return lib.data_callback, handle, destroy


@ffi.def_extern()
def request_callback(request, user_data):
    lib.shmch_incoming_request_ref(request)
    size = ffi.new("int[]", [0])
    data = lib.shmch_incoming_request_get_data(request, size)
    size = size[0]

    def respond(response: bytes):
        try:
            with g_error() as e:
                lib.shmch_incoming_request_send_response(request, response, len(response), e)
        finally:
            lib.shmch_incoming_request_unref(request)

    func = ffi.from_handle(user_data)
    func(bytes(ffi.buffer(data, size)), respond)


def wrap_request_callback(func):
    handle, destroy = wrap_user_data(func)
    return lib.request_callback, handle, destroy


@contextmanager
def g_error():
    e = ffi.new("GError**")
    yield e
    if e[0] != ffi.NULL:
        err = RuntimeError(ffi.string(lib.shmch_get_error_message(e[0])))
        lib.g_clear_error(e)
        raise err


def channel_new(name: str, role: int) -> Ptr:
    return lib.shmch_channel_new(name.encode(), role)


def channel_set_request_callback(channel: Ptr, callback: Callable):
    return lib.shmch_channel_set_request_callback(channel, *wrap_request_callback(callback))


def channel_ref(channel: Ptr):
    return lib.shmch_channel_ref(channel)


def channel_unref(channel: Ptr):
    return lib.shmch_channel_unref(channel)


def channel_open(channel: Ptr):
    with g_error() as e:
        return lib.shmch_channel_open(channel, e)


def channel_close(channel: Ptr):
    with g_error() as e:
        lib.shmch_channel_close(channel, e)


def channel_request(channel: Ptr, data: bytes, callback: Callable):
    with g_error() as e:
        return lib.shmch_channel_request(channel, data, len(data), *wrap_data_callback(callback), e)


def channel_notify(channel: Ptr, data: bytes):
    with g_error() as e:
        return lib.shmch_channel_notify(channel, data, len(data), e)


def channel_set_notification_callback(channel: Ptr, callback: Callable):
    return lib.shmch_channel_set_notification_callback(channel, *wrap_data_callback(callback))


def channel_send_receive(channel: Ptr, wait: bool):
    with g_error() as e:
        return lib.shmch_channel_send_receive(channel, wait, e)
