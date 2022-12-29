# LocalThingsNet\Examples\Quick Server summary.py

"""This is a very quick summary of the network.Server class.

The summary also extends to the network.MainServer class. For a detailed
explanation refer to the Server Demonstration notebook on the Project
repository (https://github.com/OmegaDawn/localthingsnet).

*NOTE: This file is not meant to be executed*
"""


from localthingsnet.network import Server


# Initialize Server
s = Server(servername='server', preferredport='>4000', preferreddataport='<3999',
           max_datasize=1024, adminkey='', description='')
s.startServer(maindatasock=True, services=True)
s.restartServer()
s.shutdownServer()


# New datasock
s.newDataSock(sockname='datasock1', recvFunc=s.recvClientData,
              connect_clients=['*clientid*'], connect_new_clients=True,
              show_info=False)


# New datasock with custom receiving function
@Server.recvFunctionWrapper  # Important
def customRecvFunc(self, datasock, clientid):
    bytes = datasock.recv(self.se_max_datasize)
    print(f"Received {bytes} bytes from {s.conns[clientid]['username']}")
s.newDataSock('datasock2', recvFunc=customRecvFunc)
s.closeDataSock('datasock1')


# New servercommand
def command(id, args): pass  # Always gets these two arguments
s.newServerCommand(name='example', description='', action=command,
                   needed_permission='admin', args=['arg1', 'arg2', 'arg3'],
                   optional_args=['args2', 'arg2'], repeatable_arg='arg3',
                   category='statistic', overwrite=False)
s.delServerCommand('example')


# New serverrequestable
s.newServerRequestable(name='example', data='*some_data_any_datatype*',
                       overwrite=False)
s.delServerCommand('example')


# New Service
def service_func(): pass
s.newService(name='example', service_func=service_func, as_thread=False,
             enabled=True, overwrite=False)
s.delService('example')


# Control services
s.setServiceEnabled(name='example', enable=False)
s.servicesController()


# Interact with clients
s.sendMsgTo('*some_clientid*', message='Hello world!')
s.sendDataTo('*clientid_or_socket*', data='*some_data_any_type_or_object*')
s.sendCommandTo('*clientid_or_socket*', 'COMMAND', ['arg1', 'arg2'])
data = s.sendRequestTo('*id_or_socket*', requested='*client_requestable*')
s.disconnectConn('*some clientid*')


# Output
s.printInfo('')
s.connectionInfo('')
s.warningInfo('')
s.errorInfo('')
s.logEvent('')


# Get a socket of a client
client_main_socket = s.mainSocketof(s.getIDof(username=''))
some_client_socket = s.getSocketof(s.getIDof(username=''), 4000)
all_client_sockets = s.conns[s.getIDof(username='')]['socks']


# Get data of any serversock
(sock, connect_new_clients, show_info, name) = s.getSockData(port=4000)


# Get client attributes
all_attributes_dict = s.conns[s.getIDof(username='')]
clientdata = s.conns[s.getIDof(username='con1')]['clientdata']
permissions = s.conns[s.getIDof(addr=('192.168.178.140', 0))]['permissions']
client_is_a_server = s.conns[s.getIDof(username='')]['isserver']


# Manually execute a servercommand
s.execServercommand('_', 'commandname', ['args'])
s.se_commands['commandname'][0]('*args')
