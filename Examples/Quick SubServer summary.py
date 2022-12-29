# LocalThingsNet\Examples\Quick SubServer summary.py

"""This is a very quick summary of the network.SubServer class.

The SubServer is a combination of Client and Server for multi-layered
networks. For detailed explanation refer to the Client, Server and
Network demonstration notebooks in the project repository
(https://github.com/OmegaDawn/localthingsnet).

*NOTE: This file is not meant to be executed*
"""


from localthingsnet.network import SubServer


# Initialize SubServer
ss = SubServer(
    servername='server',
    preferredport='>4000',
    preferreddataport='<3999',
    max_datasize=1024,
    adminkey='',
    description='')
ss.startServer(port='preferred', maindatasock=True, services=True)
ss.restartServer()
ss.shutdownServer()


# Connect to a higher server
ss.connect(addr=('', 0000), autoconnect=False, timeout=1)


# NOTE: For everything else see the Client and Server demonstration or summary
