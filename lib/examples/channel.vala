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

void main(string[] args) {
    if (args.length == 3) {
        role = args[1] == "server" ? Shmch.Mode.SERVER : Shmch.Mode.CLIENT;
        var message = args[2];
        var channel = new Shmch.Channel("/test", role);
        channel.set_notification_callback(notification_received);
        channel.set_request_callback(request_received);
        channel.open();
        channel.request(message.data, response_received);
        channel.notify(message.data);
        while (true) {
            channel.send_receive(true);
            Thread.usleep(100000);
        }
        channel.close();
    }
}
