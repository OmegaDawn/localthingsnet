# LocalThingsNet\Examples\Quick Client summary.py

"""This is a quick summary of the network.Client class.

The Client connects and interacts with a Server. For a detailed
explanation refer to the Client Demonstration notebook in the Project
repository (https://github.com/OmegaDawn/localthingsnet).

*NOTE: This file is not meant to be executed*
"""


from localthingsnet.network import Client


# Initialize client
c = Client(username='console', description='')


# Clientcommands
def command_func(arg1, arg2): pass
c.newClientCommand(name='example', action=command_func, call_as_thread=False,
                   overwrite=False)
c.delClientCommand('example')


# Clientrequestables
c.newClientRequestable(name='example', data=[1, 2, 3, "some data"],
                       overwrite=False)
c.delClientRequestable('example')


# Search for active server
addrs = c.searchServers(ports=[4000, 4001, 4002], ips='locals', only_one=False)


# Connect
c.connect(autoconnect=True)  # to a 'known' address
c.connect(('192.168.178.0', 4000))  # to a certain address


# Interact with server
c.sendMsg("Hello")
c.sendMsg("s.help()")  # Call servercommand
c.sendData(sock=c.clientsocks[4000], data='*some_data_any_datatype*')
data = c.sendRequest(sock=c.clientsocks[3999], request='*server_requestable*',
                     timeout=1.0)


# Disconnect
c.disconnect()


# Output
c.printInfo('')
c.statusInfo('')
c.warningInfo('')
c.errorInfo('')
c.logEvent('')


# Get a client socket
sock = c.clientsocks[4000]


# Get clientdata
client_data = c.getClientData()
