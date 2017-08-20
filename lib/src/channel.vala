/* This file contains an implementation of a binary message channel using POSIX shared memory and semaphores.
 * It supports server/client mode, requests with corresponding responses and notifications (without a response).
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
 * A binary message channel using POSIX shared memory and semaphores. It supports server
 * ({@link Mode.SERVER})/client ({@link Mode.CLIENT}) mode, requests ({@link request}, {@link set_request_callback})
 * with corresponding responses and notifications without a response ({@link set_notification_callback}).
 */
public class Channel {
    /**
     * The channel name.
     */
    public string name {get; private set;}
    /**
     * The channel mode.
     */
    public Mode mode {get; private set;}
    /**
     * Whether channel is open.
     */
    public bool is_opened {get; private set; default = false;}
    /**
     * Incoming packets.
     */
    private Queue<Packet?> incoming_queue = new Queue<Packet?>();
    /**
     * Outgoing packets.
     */
    private Queue<Packet?> outgoing_queue = new Queue<Packet?>();
    /**
     * Shared memory for slots.
     */
    private Shmem? shmem = null;
    /**
     * Slots for packets.
     */
    private unowned Slots? slots = null;
    /**
     * The id of the last outgoing request.
     */
    private uint last_request_id = 0;
    /**
     * The id of the last outgoing notification.
     */
    private uint last_notification_id = 0;
    /**
     * The callback to process incoming requests.
     */
    private RequestCallback? request_callback = null;
    /**
     * The callback to process incoming notifications.
     */
    private DataCallback? notification_callback = null;
    /**
     * The table to map outgoing requests with incoming responses by their id (cast to a pointer).
     */
    private HashTable<void*, OutgoingRequest> outgoing_requests = new HashTable<void*, OutgoingRequest>(
        null, null);
    /**
     * Create a new closed binary message channel.
     *
     * @param name    The channel name. It must contains only a single `/` at the very beginning
     *                 and not exceed 255 characters.
     * @param mode    The mode of the channel.
     */
    public Channel(string name, Mode mode){
        this.name = name;
        this.mode = mode;
    }

    ~Channel() {
        try {
            close();
        } catch (Error e) {
            debug("Failed to close the channel '%s' in the destructor. %s", name, e.message);
        }
    }

    /**
     * Open the channel.
     *
     * @throws Error on failure: {@link Error.ALREADY_OPEN}, {@link Error.INVALID_NAME}, {@link Error.SHM_OPEN}.
     */
    public void open() throws Error {
        if (is_opened) {
            throw new Error.ALREADY_OPEN("The channel '%s' has already been opened.", name);
        }
        switch (mode) {
        case Mode.SERVER:
            shmem = new Shmem(name, sizeof(Slots), true, true);
            slots = (Slots?) shmem.pointer;
            posix_die_if(slots.semaphore.init(1, 1) < 0, SHM_OF,
                "Failed to init a semaphore for shmem '%s'.".printf(name));
            break;
        case Mode.CLIENT:
            shmem = new Shmem(name, sizeof(Slots), false, false);
            slots = (Slots?) shmem.pointer;
            break;
        default:
            assert_not_reached();
        }
        is_opened = true;
    }

    /**
     * Set callback to be called to handle incoming requests.
     *
     * The data of the request must be used immediately or a copy must be made.
     * The callback is executed in the thread the {@link send_receive} method is called in.
     *
     * @param callback    The request callback.
     */
    public void set_request_callback(owned RequestCallback callback) {
        this.request_callback = (owned) callback;
    }

    /**
     * Set callback to be called to handle incoming notification.
     *
     * The data of the notification must be used immediately or a copy must be made.
     * The callback is executed in the thread the {@link send_receive} method is called in.
     *
     * @param callback    The notification callback.
     */
    public void set_notification_callback(owned DataCallback callback) {
        this.notification_callback = (owned) callback;
    }

    /**
     * Send a request.
     *
     * The callback is executed in the thread the {@link send_receive} method is called in.
     *
     * @param data                 The request data.
     * @param response_callback    The callback to be called when a response arrives.
     * @throws Error on failure: {@link Error.RESOURCE_LIMIT},  {@link Error.SHM_OPEN_FAILED},
     *     {@link Error.SHM_CLOSE_FAILED}.
     */
    public void request(uint8[] data, owned DataCallback response_callback) throws Error {
        bool wrapped = false;
        uint id = 0;
        do {
            id = ++last_request_id;
            if (id == 0) { // uint.MAX + 1 wraps to 0
                if (wrapped) {
                    throw new Error.RESOURCE_LIMIT("Too many pending outgoing requests.");
                } else {
                    wrapped = true;
                    id = ++last_request_id;
                }
            }
        } while (outgoing_requests.contains(id.to_pointer()));
        outgoing_requests[id.to_pointer()] = new OutgoingRequest(id, (owned) response_callback);
        var flag = mode == Mode.SERVER ? Flag.SERVER_REQUEST : Flag.CLIENT_REQUEST;
        push_outgoing_data(flag, id, data);
    }

    /**
     * Send a notification.
     *
     * @param data    The notification data.
     * @throws Error on failure: {@link Error.RESOURCE_LIMIT}, {@link Error.SHM_OPEN_FAILED},
     *     {@link Error.SHM_CLOSE_FAILED}.
     */
    public void notify(uint8[] data) throws Error {
        // TODO: How to avoid hypothetical overwriting of notifications with the same id?
        var id = ++last_notification_id;  // uint.MAX + 1 wraps to 0
        var flag = mode == Mode.SERVER ? Flag.SERVER_NOTIFICATION : Flag.CLIENT_NOTIFICATION;
        push_outgoing_data(flag, id, data);
    }

    /**
     * Queue outgoing packets.
     *
     * @param flag    Packet flag.
     * @param id      Packet id.
     * @param data    Packet data.
     * @throws Error on failure: {@link Error.SHM_OPEN_FAILED}, {@link Error.SHM_CLOSE_FAILED}.
     */
    private void push_outgoing_data(Flag flag, uint id, uint8[] data) throws Error {
        var name = "%s-%d-%u".printf(this.name, (int) flag, id);
        var size = data.length;
        var payload = new Shmem(name, size, true, false);
        Posix.memcpy(payload.pointer, data, size);
        payload.close();
        outgoing_queue.push_tail(Packet(flag, id, name));
    }

    /**
     * Send and receive messages.
     *
     * This method does the heavy lifting and should be called periodically, e. g. as an idle callback in an event loop.
     * Otherwise, no messages are sent nor received.
     *
     * @param wait    Whether to wait if the channel is currently locked by the other side. It may block then.
     * @return `True` if any data have been received or sent.
     * @throws Error on failure: {@link Error.SHM_OPEN_FAILED}, {@link Error.SHM_CLOSE_FAILED}, {@link Error.CLOSED}.
     */
    public bool send_receive(bool wait) throws Error {
        if (!is_opened) {
            throw new Error.CLOSED("The channel '%s' is closed.", name);
        }
        var result = wait ? slots.semaphore.wait() : slots.semaphore.trywait();
        if (result >= 0) {
            var sent_received = false;
            sent_received = read_slots() || sent_received;
            sent_received = write_slots(rearrange_slots()) || sent_received;
            posix_die_if(slots.semaphore.post() < 0, SHM_OF + 1,
                "Failed to release the semaphore for shmem '%s'.".printf(name));
            process_incoming_queue();
            return sent_received;
        } else {
            var err_code = Posix.errno;
            if (err_code == Posix.EINVAL) {
                throw new Error.SHM_OPEN_FAILED(
                    "The semaphore for shmem '%s' is invalid. %d: %s", name, err_code, Posix.strerror(err_code));
            }
        }
        return false;
    }

     /**
     * Read slots and queue incoming data.
     *
     * @return `true` if there are any incoming data.
     */
    private bool read_slots() {
        var received = false;
        for (var slot = 0; slot < N_SLOTS; slot++) {
            var flag = slots.packets[slot].flag;
            var accept = false;
            switch (flag) {
            case Flag.CLIENT_NOTIFICATION:
            case Flag.CLIENT_REQUEST:
            case Flag.CLIENT_RESPONSE:
                accept = mode == Mode.SERVER;
                break;
            case Flag.SERVER_NOTIFICATION:
            case Flag.SERVER_REQUEST:
            case Flag.SERVER_RESPONSE:
                accept = mode == Mode.CLIENT;
                break;
            }
            if (accept) {
                incoming_queue.push_tail(slots.packets[slot]);
                slots.packets[slot].flag = Flag.EMPTY;
                received = true;
            }
        }
        return received;
    }

    /**
     * Rearrange slots so that non-empty slots are at the beginning but preserve order.
     *
     * @return The index of the first empty slot or `-1` if there is not any.
     */
    private int rearrange_slots() {
        var first_empty = -1;
        for (var slot = 0; slot < N_SLOTS; slot++) {
            if (first_empty < 0 && slots.packets[slot].flag == Flag.EMPTY) {
                first_empty = slot;
            } else if (first_empty >= 0 && slots.packets[slot].flag != Flag.EMPTY) {
                slots.packets[first_empty] = slots.packets[slot];
                slots.packets[slot].flag = Flag.EMPTY;
                first_empty++;
            }
        }
        assert(first_empty < N_SLOTS);
        return first_empty;
    }

    /**
     * Write packets from outgoing queue.
     *
     * @param cursor    The index where to start looking for an empty slot.
     * @return `true` if any data have been written.
     */
    private bool write_slots(int cursor) {
        var sent = false;
        for (var slot = cursor; slot < N_SLOTS && !outgoing_queue.is_empty(); slot++) {
            if (slots.packets[slot].flag == Flag.EMPTY) {
                slots.packets[slot] = outgoing_queue.pop_head();
                sent = true;
            }
        }
        return sent;
    }

    /**
     * Process incoming queue and fire callbacks.
     *
     * @throws Error on failure: {@link Error.SHM_OPEN_FAILED}, {@link Error.SHM_CLOSE_FAILED}.
     */
    private void process_incoming_queue() throws Error {
        Packet? packet = null;
        while ((packet = incoming_queue.pop_head()) != null) {
            var id = packet.id;
            var payload = new Shmem((string) packet.shm_name, 0, false, true);
            unowned uint8[] data = payload.get_buffer();
            switch (packet.flag) {
            case Flag.SERVER_NOTIFICATION:
            case Flag.CLIENT_NOTIFICATION:
                if (this.notification_callback != null) {
                    this.notification_callback(data);
                }
                break;
            case Flag.SERVER_REQUEST:
            case Flag.CLIENT_REQUEST:
                if (this.request_callback != null) {
                    var request = new IncomingRequest(id, data, send_response);
                    this.request_callback(request);
                }
                break;
            case Flag.SERVER_RESPONSE:
            case Flag.CLIENT_RESPONSE:
                var request = outgoing_requests.take(id.to_pointer());
                if (request != null)
                    request.handle_response(data);
                break;
            default:
                assert_not_reached();
            }
            payload.close();
        }
    }

    /**
     * Send a response back to caller.
     *
     * @param id    The response id.
     * @param data    The response data
     * @throws Error on failure: {@link Error.SHM_OPEN_FAILED}, {@link Error.SHM_CLOSE_FAILED}.
     */
    private void send_response(uint id, uint8[] data) throws Error {
       var flag = mode == Mode.SERVER ? Flag.SERVER_RESPONSE : Flag.CLIENT_RESPONSE;
       push_outgoing_data(flag, id, data);
    }

    /**
     * Close the channel
     *
     * @throws Error on failure: {@link Error.CLOSED}, {@link Error.SHM_CLOSE_FAILED}.
     */
    public void close() throws Error {
        if (!is_opened) {
            throw new Error.CLOSED("The channel '%s' is closed.", name);
        }
        if (mode == Mode.SERVER) {
            slots.semaphore.destroy();
        }
        slots = null;
        try {
            shmem.close();
        } finally {
            shmem = null;
            is_opened = false;
        }
    }
}

} // namespace Shmch

