/* This file contains a few utility functions, especially for POSIX error handling.
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
 * Return an error message from an error.
 *
 * This is useful for binding.
 *
 * @param e    The error.
 * @return Error message.
 */
public string get_error_message(GLib.Error e) {
    return e.message;
}


/**
 * Warn if a POSIX call fails.
 *
 * The warning includes the original error message.
 *
 * @param failed     The failure indicator.
 * @param message    The message to be prepended to the original POSIX error message.
 */
private inline void posix_warn_if(bool failed, string message) {
    if (failed) {
        var err_code = Posix.errno;
        var err_message = Posix.strerror(err_code);
        warning("%s %d:%s", message, err_code, err_message);
    }
}


/**
 * Throw an error if a POSIX call fails.
 *
 * The error includes the original error message.
 *
 * @param failed     The failure indicator.
 * @param code       The code of {@link Error} domain error.
 * @param message    The message to be prepended to the original POSIX error message.
 * @throws Error if `failed` is `true`.
 */
private inline void posix_die_if(bool failed, int code, string message) throws Error {
    if (failed) {
        var err_code = Posix.errno;
        var err_message = Posix.strerror(err_code);
        Error err = (Error) new GLib.Error(Error.quark(), code, "%s %d:%s".printf(message, err_code, err_message));
        throw err;
    }
}

} // namespace Shmch
