const shmch = require('./build/Debug/_shmchannel.node')


function encodeStringAsUTF8(string) {
  let charList = unescape(encodeURIComponent(string)).split('')
  let uintArray = []
  for (let i = 0; i < charList.length; i++) {
    uintArray.push(charList[i].charCodeAt(0))
  }
  return new Uint8Array(uintArray)
}


function decodeUTF8String(uint8Array) {
  let encodedString = String.fromCharCode.apply(null, uint8Array)
  return decodeURIComponent(escape(encodedString))
}


const Channel = function(name, mode, requestCallback, notificationCallback, dataConverter) {
  this.name = name
  this.mode = mode
  this.dataConverter = dataConverter || null
  this.running = false
  this._channel = new shmch.Channel(name, mode)
  this.requestCallback = requestCallback || null
  this.notificationCallback = notificationCallback || null
  this._channel.setRequestCallback(this.onRequestReceived.bind(this))
  this._channel.setNotificationCallback(this.onNotificationReceived.bind(this))

}

Channel.prototype.setNotificationCallback = function(callback){
  this.notificationCallback =callback
}

Channel.prototype.setRequestCallback = function(callback){
  this.requestCallback= callback
}

Channel.prototype.open = function(){
  this._channel.open()
}

Channel.prototype.close = function(){
  this._channel.close()
}


Channel.prototype.notify = function (data) {
  let [bytes, length] = this.dataConverter ? this.dataConverter.toBytes(data) : [data, data.byteLength]
  this._channel.notify(bytes, length)
}

Channel.prototype.startCommunication = async function () {
  this.running = true
  while (this.running) {
    this._channel.sendReceive(false)
    let promise = new Promise(function(resolve, reject){
      setTimeout(resolve, 10)
    })
    await promise;
  }
}

Channel.prototype.stopCommunication = function() {
  this.running = false;
}

Channel.prototype.request = async function(data) {
  let [bytes, length] = this.dataConverter ? this.dataConverter.toBytes(data) : [data, data.byteLength]
  let channel = this._channel
  let requestAsync = function (resolve, reject) {
    try {
      channel.request(bytes, length, resolve)
    } catch (e) {
      reject(e)
    }
  }
  let response = await new Promise(requestAsync)
  return this.dataConverter ? this.dataConverter.fromBytes(response) : response
}

Channel.prototype.onNotificationReceived = function(data) {
  if (this.notificationCallback) {
    this.notificationCallback(this.dataConverter ? this.dataConverter.fromBytes(data) : data)
  }
}

Channel.prototype.onRequestReceived = function(request) {
  let data = request.getData()
  console.log("request received: %s", data)
  if (this.requestCallback) {
    if (this.dataConverter) {
      data = this.dataConverter.fromBytes(data)
    }
    let that = this
    let respond = function(response) {
      console.log("send response: %s", data)
      let [bytes, length] = that.dataConverter ? that.dataConverter.toBytes(response) : [response, response.byteLength]
      request.sendResponse(bytes, length)
      console.log("send response done: %s", data)
    }
    this.requestCallback(data, respond)
  } else {
    request.sendResponse(data, data.byteLength)
  }
}


const StringDataConverter = function() {

}

StringDataConverter.prototype.toBytes = function(data) {
  let bytes = encodeStringAsUTF8(data)
  return [bytes.buffer, bytes.buffer.byteLength]
}


StringDataConverter.prototype.fromBytes = function (data) {
  return decodeUTF8String(new Uint8Array(data))
}

const MODE_SERVER = 0
const MODE_CLIENT = 1

module.exports = {Channel, StringDataConverter,encodeStringAsUTF8, decodeUTF8String, MODE_CLIENT, MODE_SERVER}
