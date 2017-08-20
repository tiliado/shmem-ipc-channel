/* This file contains definition of callbacks (DataCallback, SendResponseFunc, RequestCallback),
 * error domains (Error), enumerations (Mode, Flag), data structures (Packet, Slots), and
 * data classes (OutgoingRequest, IncomingReques).
 *
 * Copyright 2017 Jiří Janoušek <janousek.jiri@gmail.com>
 *
 * Licensed under the BSD-2-Clause license:
 *
 * Redistribution and use in source and binary forms, with or without* modification, are permitted provided that the
 * following conditions are met:
 *
 * 1. Redistributions of source code must retain the above copyright notice, this list of conditions and the following
 *    disclaimer.
 * 2. Redistributions in binary form must reproduce the above copyright notice, this list of conditions and the
 *    following disclaimer in the documentation and/or other materials provided with the distribution.
 *
 * THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES,
 * INCLUDING, BUT NOT LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
 * DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT OWNER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
 * SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR
 * SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY,
 * WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE
 * USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE. */

namespace Shmch {

/**
 * The callback to be called when data is available.
 *
 * @param data    The data to process.
 */
public delegate void DataCallback(uint8[] data);

/**
 * The callback to call when a response is available.
 *
 * @param id      The request id.
 * @param data    The data of the response.
 * @throws Error on failure.
 */
private delegate void SendResponseFunc(uint id, uint8[] data) throws Error;

/**
 * The callback to be called when a new request arrives.
 *
 * @param request    The request to process.
 */
public delegate void RequestCallback(IncomingRequest request);

/**
 * Shared memory channel errors
 */
public errordomain Error {
    /**
     * The resource has already been opened.
     */
    ALREADY_OPEN,
    /**
     * The resource is closed.
     */
    CLOSED,
    /**
     * The name of shared memory is not valid.
     */
    INVALID_NAME,
    /**
     * The size of shared memory is not valid.
     */
    INVALID_SIZE,
    /**
     * Failed to open shared memory or set its size up.
     */
    SHM_OPEN_FAILED,
    /**
     * Failed to close shared memory.
     */
    SHM_CLOSE_FAILED,
    /**
     * When the requested action cannot be performed because of a resource limit.
     */
    RESOURCE_LIMIT;

    /**
     * Return the quark of this error domain.
     *
     * @return The quark of this error domain.
     */
    public extern static GLib.Quark quark();
}


private const int SHM_OF = 4; // Error.SHM_OPEN_FAILED


/**
 * The mode of the channel.
 */
public enum Mode {
    /**
     * The server creates a shared memory channel and destroys it upon exit.
     */
    SERVER,
    /**
     * The client connects to an existing shared memory channel and does not
     * interact with its life cycle.
     */
    CLIENT;
}


/**
 * Packet flags.
 */
private enum Flag {
    /**
     * The packet is empty.
     */
    EMPTY,
    /**
     * The packet contains a request sent from the server to the client.
     */
     SERVER_REQUEST,
     /**
     * The packet contains a request sent from the client to the server.
     */
     CLIENT_REQUEST,
     /**
     * The packet contains a response sent from the server to the client.
     */
     SERVER_RESPONSE,

     /**
     * The packet contains a response sent from the client to the server.
     */
     CLIENT_RESPONSE,
     /**
     * The packet contains a notification sent from the server to the client.
     */
     SERVER_NOTIFICATION,
     /**
     * The packet contains a notification sent from the client to the server.
     */
     CLIENT_NOTIFICATION;
}


/**
 * The metadata of payload sent through the shared memory channel,
 */
private struct Packet {
    /**
     * The purpose of this packet. See {@link Flag} for more details.
     */
    public Flag flag;
    /**
     * The packed id.
     */
    public uint id;
    /**
     * The name of the shared memory region where the data of this packet are.
     */
    public uint8 shm_name[255];

    /**
     * Create new packet metadata.
     *
     * @param flag        The purpose of this packet. See {@link Flag} for more details.
     * @param id          The packed id used to pair requests with responses. Irrelevant for notifications.
     * @param shm_name    The name of the shared memory region where the data of this packet are.
     */
    public Packet(Flag flag, uint id, string shm_name) {
        this.flag = flag;
        this.id = id;
        Posix.memcpy(this.shm_name, shm_name.data, shm_name.length + 1);
    }
}


/**
 * The number of slots in {@link Slots}
 */
private const int N_SLOTS = 10;


/**
 * The structure to exchange packets via shared memory.
 * Access is guarded by the included semaphore.
 */
private struct Slots {
    /**
     * The semaphore to control access to this structure.
     */
    public Sem semaphore;
    /**
     * Slots for packet metadata.
     */
    public Packet packets[10];
}


/**
 * The metadata of pending outgoing request.
 */
private  class OutgoingRequest {
    /**
     * The request id.
     */
    public uint id;

    /**
     * The callback to handle the response once it is available.
     */
    private DataCallback response_callback;

    /**
     * Create a new metadata object for a pending outgoing request.
     *
     * @param id                   The request id.
     * @param response_callback    The callback to handle the response once it is available.
     */
    public OutgoingRequest(uint id, owned DataCallback response_callback) {
        this.id = id;
        this.response_callback = (owned) response_callback;
    }

    /**
     * Pass the response to the caller.
     *
     * @param data    The response data,
     */
    public void handle_response(uint8[] data) {
        response_callback(data);
    }
}

/**
 * The metadata of an incoming request to be processed.
 */
public class IncomingRequest {
    /**
     * The request id.
     */
    private uint id;
    /**
     * The data of this request.
     */
    private unowned uint8[] data;
    /**
     * The callback to be called to send response.
     */
    private SendResponseFunc response_callback;

    /**
     * Create new incoming request metadata object.
     *
     * @param id                  The request id.
     * @param data                The request data. Use it immediately with {@link get_data}
     *                             or make a copy for later processing.
     * @param response_callback    The callback to be called to send a response.
     */
    internal IncomingRequest(uint id, uint8[] data, owned SendResponseFunc response_callback) {
        this.id = id;
        this.data = data;
        this.response_callback = (owned) response_callback;
    }

    /**
     * Get response data.
     *
     * Call this function immediately upon request arrival and make a copy for later processing.
     */
    public unowned uint8[]? get_data() {
        return (this.data == null) ? null : this.data;
    }

    /**
     * Send a response to the caller.
     *
     * @param data    The response data.
     * @throws Error on failure.
     */
    public void send_response(uint8[] data) throws Error {
        if (this.response_callback != null) {
            this.response_callback(this.id, data);
            this.response_callback = null;
        }
    }
}

} // namespace Shm
