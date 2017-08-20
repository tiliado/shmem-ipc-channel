/* This file contains a wrapper around POSIX shared memory primitives.
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
 * A wrapper around POSIX shared memory primitives.
 */
public class Shmem {
    /**
     * The shared memory name.
     */
    public string name {get; private set; default = null;}
    /**
     * The actual shared memory size.
     */
    public ulong size {get; private set; default = 0;}
    /**
     * The pointer to the shared memory buffer.
     */
    public void* pointer {get; private set; default = null;}
    /**
     * The shared memory fd.
     */
    private int fd = -1;
    /**
     * Whether to discard shared memory upon {@link close}.
     */
    private bool discard = false;

    /**
     * Create or open POSIX shared memory.
     *
     * Use {@link pointer} and {@link get_buffer} to access the shared memory region with the actual size {@link size}.
     * Then {@link close} the shared memory when no longer needed. It is also automatically closed in destructor,
     * but you should not count on it. Explicit is better than implicit in case of resources.
     *
     * @param name       The shared memory name. It must contains only a single `/` at the very beginning
     *                    and not exceed 255 characters.
     * @param size       The shared memory size. It may be 0 if `create` is `true` and the actual size will
     *                    used instead and available as {@link size}.
     * @param create     Whether to create new shared memory region or to open an existing one.
     * @param discard    Whether to discard the shared memory region or let it be alive upon {@link close}.
     * @throws Error on failure: {@link Error.INVALID_NAME}, {@link Error.INVALID_SIZE},
     *     {@link Error.SHM_OPEN_FAILED}.
     */
    public Shmem(string name, ulong size, bool create, bool discard) throws Error {
        if (name == null || name[0] != '/' || name.index_of_char('/', 1) >= 0 || name.length > 255) {
            throw new Error.INVALID_NAME("The shmem name '%s' is invalid.", name);
        }
        this.name = name;
        this.size = size;
        this.discard = discard;
        if (create) {
            if (size == 0) {
                throw new Error.INVALID_SIZE("Size > 0 must be specified to create shmem '%s'.", name);
            }
            shm_unlink(name);
            fd = shm_open(name, Posix.O_CREAT|Posix.O_EXCL|Posix.O_RDWR, Posix.S_IRUSR|Posix.S_IWUSR);
            posix_die_if(fd < 0, 1, "Failed to open shmem '%s'.".printf(name));
            try {
                try {
                    posix_die_if(Posix.ftruncate(fd, size) < 0, SHM_OF, "Failed to set shmem '%s' size.".printf(name));
                    void* buf = Posix.mmap(null, size, Posix.PROT_READ|Posix.PROT_WRITE, Posix.MAP_SHARED, fd, 0);
                    posix_die_if(Posix.MAP_FAILED == buf, SHM_OF, "Failed to map shmem '%s' size.".printf(name));
                    this.pointer = buf;
                } finally {
                    posix_warn_if(Posix.close(fd) < 0, "Failed to close shmem '%s' fd.".printf(name));
                    fd = -1;
                }
            } catch (Error e) {
                size = 0;
                pointer = null;
                shm_unlink(name);
                throw e;
            }
        } else {
            fd = shm_open(name, Posix.O_RDWR, 0);
            posix_die_if(fd < 0, 1, "Failed to open shm '%s'.".printf(name));
            try {
                try {
                    Posix.Stat stat;
                    posix_die_if(Posix.fstat(fd, out stat) < 0, SHM_OF, "Failed to stat shm '%s'.".printf(name));
                    if (size == 0) {
                        this.size = size = stat.st_size;
                    } else if (size > stat.st_size) {
                        throw new Error.INVALID_SIZE(
                            "The specified size %s of shmem '%s' is greater than the actual size %d.",
                            size.to_string(), name, (int) stat.st_size);
                    }
                    void* buf = Posix.mmap(null, size, Posix.PROT_READ|Posix.PROT_WRITE, Posix.MAP_SHARED, fd, 0);
                    posix_die_if(Posix.MAP_FAILED == buf, SHM_OF, "Failed to map shmem '%s'.".printf(name));
                    this.pointer = buf;
                } finally {
                    posix_warn_if(Posix.close(fd) < 0, "Failed to close shmem '%s' fd.".printf(name));
                    fd = -1;
                }
            } catch (Error e) {
                size = 0;
                pointer = null;
                throw e;
            }
        }
    }

    ~Shmem() {
        try {
            close();
        } catch (Error e) {
            warning("Failed to close shmem '%s' in destructor.", name);
        }
    }

    /**
     * Get shared memory as a binary buffer.
     */
    public unowned uint8[] get_buffer() {
        unowned uint8[] data = (uint8[]) pointer;
        data.length = (int) size;
        return data;
    }

    /**
     * Close the shared memory.
     *
     * If it was opened with `discard` = `true`, it will be deleted as soon as when possible.
     */
    public void close() throws Error {
        if (size > 0) {
            posix_die_if(Posix.munmap(pointer, size) < 0, SHM_OF + 1, "Failed to unmap shmem '%s'.".printf(name));
            size = 0;
        }
        pointer = null;
        fd = -1;
        if (discard) {
            shm_unlink(name);
            discard = false;
        }
    }
}

} //namespace Shmch
