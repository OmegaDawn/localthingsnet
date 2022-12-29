# LocalThingsNetwork
Networking module for personal IoT projects.

---
## Description
The ***localthingsnet(work)*** Project is a Python module for applications that
require a simple way of communication with other devices in the same *(local)*
network. Based on [socket](https://docs.python.org/3/library/socket.html) this
module provides server-client interactions through one or multiple sockets and
multi-layered networks are also possible. Everything regarding the socket
setup, binding/connecting and receiving is handled by the module. Apart from
transmitting data, predefined requestables and commands can be used to get
certain data from the other instance or execute scripts on the other machine.

---
## How to Use the Project
Clone or download the repository and put the `localthingsnet` folder in the
`lib` folder of your python installation so that it can be imported with
`import localthingsnet.network as ltn`.

The repository holds an examples folder with demonstrations notebooks that
explain the functionality of the module in depth. There are also short
summaries that present the most important functions.

Apart from that a simple example is shown below:

```
# Initiate server
s = Server()
s.startServer()

# Initiate and connect client
c = Client()
c.connect(s.addr)

# Interact with server
c.sendMsg("Hello Server")
c.sendMsg("s.help()")
data = c.sendRequest(c.clientsocks[s.addr[1]], 'Serverdata')
```

---
## License
GNU General Public License v3.0
