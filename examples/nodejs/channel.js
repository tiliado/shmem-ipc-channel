const {Channel, StringDataConverter, MODE_CLIENT, MODE_SERVER} = require('shmchannel')

function onNotification(data) {
  console.log("Notification received: %sn", data)
}

function onRequest(data, respond) {
  console.log("Request received: %s", data)
  respond("You have sent: " + data)
}

async function main(args) {
  if (args.length === 4) {
    let role = args[2] === "server" ? MODE_SERVER : MODE_CLIENT
    let message = args[3]
    let channel = new Channel("/test", role, onRequest, onNotification, new StringDataConverter())
    channel.open()
    let loop = channel.startCommunication()
    console.log("Request sent: %s", message)
    let response = await channel.request(message)
    console.log("Response received: %s", response)
    channel.notify(message)
    await loop
    channel.close()
    return 0;
  } else {
    console.log("Usage: %s %s server|client message", args[0], args[1]);
    return 1;
  }
}

main(process.argv).catch(function (e) {
  console.log("Error: %s", e)
})
