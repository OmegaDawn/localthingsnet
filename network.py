#!/usr/bin/env python3.11.0
# -*- coding: utf-8 -*-
# LocalThingsNet\network.py

"""Socket based communication tool for personal Projects.

...

The `LocalThingsNetwork.network` module provides a way of communication
between devices in local networks. The network follows the Server-Client
concept of `socket`_ and the module handles all socket related things.
The network parties exchange data on demand(/request) or if wanted and
the execution of predefined commands on the other machine is also
possible. For larger projects multi layer networks can be initiated.

---
Project Repository
------------------
For more information about the *LocalThingsNetwork* project, visit the
`project repository`_.
For usage examples refer to the `demonstration notebooks and summaries`_

---
Documentation Information
-------------------------
The documentation style is based on `numpydoc`_ style. Words embedded in
single asterisk refer to proper names of entities. Code snippets are
indicated by three greater-than signs:

>>> x = 42
>>> x = x + 1
>>> for i in range(2):
...     print(i)
0
1

Parameters mentioned in a docstring are marked with two asterisk or
rendered as bold like in the following example:

>>> def add(param1, param2):
...     '''The **param1** is added to **param2**.'''
...     return param1 + param2

It is assumed that the following instances are/get initialized:

>>> import localthingsnet.network as ltn
>>> c = Client()
>>> s = Server()
>>> ss = SubServer()
>>> ms = MainServer(port=4000)


.. _socket:
   https://docs.python.org/3/library/socket.html
.. _numpydoc:
    https://numpydoc.readthedocs.io/en/latest/format.html
.. _project repository:
    https://github.com/OmegaDawn/localthingsnet
.. _demonstration notebooks and summaries:
    https://github.com/OmegaDawn/localthingsnet/tree/master/Examples
"""


from pickle import PicklingError, UnpicklingError, dumps, loads
from socket import socket, AF_INET, SOCK_DGRAM, SOCK_STREAM
from typing import Optional, Callable, Iterable, Any
from threading import enumerate as thread_enumerate
from threading import Thread
from itertools import count
from datetime import datetime
from time import time, sleep
from uuid import uuid4
from re import compile
from os import system


__version__ = '1.0.0'
__date__ = '2022/12/29'
__author__ = 'Laurenz Nitsche'


class Client:
    """Client for interactions with a server.

    ...

    The Client can search for active servers and connect to the
    *serversock* on a found address. After a successful registration,
    the client is connected and can interact with the server. Additional
    *datasocks* get automatically connected if set by the server. This
    happens through the use of **clientcommands** which allow the server
    to execute short predefined scripts on the client machine. The
    client can send python objects to the server. *(Other sorts of data
    can be transmitted with custom datasocks)*. Text that is sent to the
    server can include *servercommands*. Additionally **data requests**
    allow the client to request data from the server.

    ---
    Attributes
    ----------
    autoconnect_addrs : list
        Addresses that are/were used by a server
        list[tuple[ip:str, port:int]]
    cl_commands : dict
        All available clientcommands
        dict[name:str, tuple[func:Callable, call_as_thread:bool]]
    cl_max_datasize : int
        Maximum bytes that get sent/received at once
    cl_requestables : dict
        All available client requestables
        dict[id:str, data:object]
    cl_serverdata : dict[str, Any]
        Metadata of the connected server
    clientsocks : dict
        Sockets connected with the server
        dict[port:int, socket]
    connected_addr : tuple
        Address of the connected server
        tuple(ip:str, port:int)
    connected : bool
        Client is connected to a server
    description : str
        Short information text about the client
    ip : str
        IP of the client
    layer : int
        Depth layer in the network
    logfile : str
        Filename that saves occurred events
    starttime : float
        Time the client was initialized
    username : str
        Username of the client
    _ansi : bool
        Allow ANSI text formatting
    _cl_sep: str
        Separator identifies end of transmitted package
    _connecting : bool
        Client is executing a *connect()* call
    _connecttime : float
        Time the client connected to a server
    _conntype : str
        Application type of the client
    _log : list[str]
        All occurred events
    _open_requests : dict
        Unanswered data requests
        dict[id:str, request_or_data:object]

    ---
    Notes
    -----
    - The *serversock* is the main socket of a server and *Datasocks*
    are sockets of a server that are used for custom data transfer.
    - *Servercommands* are similar to **clientcommands**.
    - *Serverrequestables* are similar to **clientrequestables**.

    ---
    Clientcommands
    --------------
    - connect
    - disconnect
    - newdatasock
    - setlayer
    - updateserverdata
    - changename

    ---
    Clientrequestables
    ------------------
    - CLIENTDATA
    - PING

    ---
    Examples
    --------
    >>> c = Client()
    >>> c.connect('192.168.178.200', 4000)
    >>> c.sendMsg("Hello World")
    >>> c.disconnect()
    """

    __version__ = '6.26.136'

    def __init__(self, username: str = '', description: str = "None",
                 logfile: str = '', ansi: bool = True):
        """...

        Parameters
        ----------
        username : str, optional
            Username of the client
        description : str, optional
            Information text about the client
        logfile : str, optional
            Path to file that stores all occurred events
        ansi : bool, optional
            Allow *ANSI* text formatting codes

        ---
        Notes
        -----
        - The **description** should state the abilities or purpose of
        the client.

        ---
        Examples
        --------
        >>> c = Client('con', "Demonstration client", 'log.txt')
        """

        self.username = username
        self.description = description
        self.logfile = logfile
        self._ansi = ansi

        self.clientsocks: dict[int, socket] = {}
        self.cl_commands: dict[str, tuple[Callable, bool]] = {}
        self.cl_requestables: dict[str, object] = {}
        self.cl_serverdata: dict[str, Any] = {}
        self.autoconnect_addrs: list[tuple[str, int]] = []
        self._open_requests: dict[str, object] = {}
        self._log: list[str] = []
        self._starttime: float = time()
        self._connecttime: float = 0.0
        self._connecting: bool = False
        self._conntype = 'CLIENT'

        # Variables that get set with a connection
        self.connected: bool = False
        self.connected_addr: tuple[str, int] = ('', -1)
        self.cl_max_datasize: int = 1024
        self._cl_sep: str = ''
        self.layer: int = 0

        # Getting the ip with gethostname() doesn't work for raspberry
        s = socket(AF_INET, SOCK_DGRAM)
        s.connect(('1.1.1.1', 1))
        self.ip: str = s.getsockname()[0]
        s.close()

        # Display ANSI formatting on windows
        if self._ansi: system("")

        Client._initClientcommands(self)
        Client._initClientRequestables(self)

        if self.logfile != '':
            self.logEvent(f"Storing log '{self.logfile}'")
            open(self.logfile, 'w').close()
        self.logEvent(f"Client ({Client.__version__}|{self._conntype}) loaded")

    def newClientCommand(self, name: str, action: Callable,
                         call_as_thread: bool = False,
                         overwrite: bool = False):
        """Creates or changes a clientcommand.

        ...

        Defines an action that gets made when a connected server calls
        this command. A runtime inexpensive **action** can be called
        without the need of a new thread. A runtime expensive **action**
        should be called in a new thread to prevent an unresponsive
        socket. Actions can have parameters.

        The command receiving socket can be passed to **action** if the
        first parameter of **action** is named *'calling_socket'*.

        ---
        Parameters
        ----------
        name : str
            Name of the clientcommand
        action : Callable
            Script that gets executed with the command
        call_as_thread : bool, optional
            The command gets called as a new thread
        overwrite : bool, optional
            Overwrite an existing command

        ---
        Raises
        ------
        NameError : If the command is already in use and not overwritten

        ---
        See Also
        --------
        delClientCommand : Delete a clientcommand

        ---
        Notes
        -----
        - If a **action** is not called as thread, the
        `recvServerData()` thread for a socket executes the *action* and
        is therefore unable to receive data from that socket until the
        **action** finishes executing.
        - Clientcommands should be written in lowercase.

        ---
        Examples
        --------
        >>> c.newClientCommand('print_text', lambda text: print(text))

        >>> def big_calculation(socket, par1, par2):
        ...     pass  # Do some runtime expensive calculation
        >>> c.newClientCommand('calculate', big_calculation,
        ...                       call_as_thread=True)

        >>> def send_back(calling_socket, received)
        ...     calling_socket.send(received.encode())
        >>> c.newClientCommand('send_back', send_back)
        """

        if name in self.cl_commands and not overwrite:
            raise NameError(f"Clientcommand '{name}' already exists")
        if name not in self.cl_commands and overwrite:
            self.warningInfo(
                f"Creating new clientcommand since no '{name}' exists")
        self.cl_commands[name] = (action, call_as_thread)

    def delClientCommand(self, name: str):
        """Deletes a clientcommand.

        ...

        ---
        Parameters
        ----------
        name : str
            Name of the commands that gets deleted

        ---
        Raises
        ------
        NameError : No command with given name

        ---
        See Also
        --------
        executeClientCommand : Execute a clientcommand
        newClientCommand : Define a new clientcommand

        ---
        Examples
        --------
        >>> c.newClientCommand("print_text", lambda text: print(text))
        >>> c.delClientCommand("print_text")
        """

        if name in self.cl_commands:
            del self.cl_commands[name]
        else:
            raise NameError(f"No Clientcommand named '{name}'")

    def newClientRequestable(self, name: str, data: object,
                             overwrite: bool = False):
        """Creates or changes a client requestable.

        (Client)requestables allow the server to request certain data
        from the client. What data can be requested if defined by the
        client.

        -----

        Parameters
        ----------
        name : str
            Name of the requestable
        data : object
            Data that gets requested
        overwrite : bool, optional
            Overwrite an existing requestable

        ---
        Raises
        ------
        NameError : The requestable is already used and not overwritten

        ---
        See Also
        --------
        delClientRequestable : Delete a client requestable

        ---
        Notes
        -----
        - **data** can also be a function with a return value.
        - Requestables should be written in uppercase.

        ---
        Examples
        --------
        >>> c.newClientRequestable('PI', 3.1415)

        >>> import time
        >>> c.newClientRequestable('TIME', lambda: time())
        """

        if name in self.cl_requestables and not overwrite:
            raise NameError(
                f"Requestable data through '{name}' already exists")
        if name not in self.cl_requestables and overwrite:
            self.warningInfo(
                f"Creating new requestable since no key '{name}' exists")
        self.cl_requestables[name] = data

    def delClientRequestable(self, name: str):
        """Deletes a client requestable.

        ...

        ---
        Parameters
        ----------
        name : str
            Name of the requestable that gets deleted

        ---
        See Also
        --------
        newClientRequestable : Define a new client requestable

        ---
        Examples
        --------
        >>> c.newClientRequestable('PI', 3.1415)
        >>> c.delClientRequestable('PI')
        """

        if name in self.cl_requestables:
            del self.cl_requestables[name]
        else:
            raise NameError(f"No ClientRequestable named '{name}'")

    def execClientCommand(self, received_socket: socket, command: str,
                          args: list[object]):
        """Executes a clientcommand sent by the server.

        ...

        Handles thread creation for clientcommands that are called as
        threads and general execution of clientcommands.

        ---
        Parameters
        ----------
        received_socket : socket
            Socket that received the command
        command : str
            Name of the command
        args : list[object]
            Arguments for the command

        ---
        See Also
        --------
        newClientCommand : Define a new clientcommand

        ---
        Examples
        --------
        >>> c.newClientCommand('print_text', lambda text: print(text))
        >>> sock = c._clientsocks[4000]  # Port to a connected socket
        >>> c.execClientCommand(sock, 'print_text', ["Hello World!"])
        """

        if command not in self.cl_commands:
            self.warningInfo(f"Unknown clientcommand '{command}'")
        elif self.cl_commands[command][1]:
            if self.cl_commands[command][0].__code__.co_varnames[0] == \
            'calling_socket':
                Thread(
                    target=self.cl_commands[command][0],
                    args=(received_socket, *args,),
                    name=f'clientcommand_{command}'
                ).start()
            else:
                Thread(
                    target=self.cl_commands[command][0],
                    args=(*args,),
                    name=f'clientcommand_{command}'
                ).start()
        else:
            try:
                if self.cl_commands[command][0].__code__.co_varnames[0] ==\
                'calling_socket':
                    self.cl_commands[command][0](received_socket, *args)
                else:
                    self.cl_commands[command][0](*args)
            except Exception as e:
                self.errorInfo("Error while executing clientcommand "
                                + f"'{command}': {str(e)}")

    def _initClientcommands(self):
        """Initiates available clientcommands.

        ...

        Initiated clientcommands
        - connect
        - disconnect
        - newdatasock
        - setlayer
        - updateserverdata
        - changename

        ---
        See Also
        --------
        newClientCommand : Define a new clientcommand

        ---
        Notes
        -----
        - Gets called as `Client.initClientCommand(self)` with the
        initialization of a client.
        """

        def changename(name):
            self.username = name

        def setlayer(layer):
            self.layer = layer

        def updateserverdata(data):
            self.cl_serverdata = data

        def connect(ip, port):
            Thread(
                target=self.connect,
                args=((ip, int(port)), False,),
                name='connect'
            ).start()

        self.newClientCommand('changename', changename)
        self.newClientCommand('setlayer', setlayer)
        self.newClientCommand('updateserverdata', updateserverdata)
        self.newClientCommand('disconnect', self.disconnect, True)
        self.newClientCommand('connect', connect)
        self.newClientCommand('newdatasock', self.connectDatasock)

    def _initClientRequestables(self):
        """Initiates clientrequestables that get requested by a server.

        ...

        Initiated clientrequestables:
        - PING
        - CLIENTDATA

        ---
        See Also
        --------
        newClientRequestable : Define a new client requestable

        ---
        Notes
        -----
        - Gets called as `Client._initClientRequestables(self)` with the
        initialization of a client.
        """

        self.newClientRequestable('PING', lambda: time())
        self.newClientRequestable('CLIENTDATA', lambda: self.getClientData())

    # ----------------------------------+
    # Connect and communication methods |
    # ----------------------------------+

    def disconnect(self):
        """Terminates a connection.

        ...

        Disconnects every connected socket and resets all variables.

        ---
        Notes
        -----
        - The`recvClientData()` threads for connected socket also tries
        to disconnect and remove the socket. Both instances are
        required.

        """

        servername = self.cl_serverdata['servername'] if 'servername' in \
            self.cl_serverdata else ''
        self.connected = False
        self._connecting = False
        self.connected_addr = ('', -1)
        self.cl_serverdata = {}
        self._connecttime = 0.0
        self._cl_sep = ''
        self.layer = 0

        started = time()
        # Disconnect all socket (through this loop or receiving threads)
        while len(self.clientsocks) > 0:
            try:
                sock = self.clientsocks[list(self.clientsocks.keys())[0]]
                del self.clientsocks[self.getPort(sock)]
                sock.close()
            # Socket got removed by a receiving thread
            except (ValueError, KeyError):
                pass
            if time() - started > 1.5:
                self.errorInfo("Failed to correctly disconnect the client")
                return
        if self._conntype != 'SERVERFINDER':
            if servername != '':
                self.statusInfo(f"Disconnected from Server '{servername}'")
            else:
                self.statusInfo("Disconnected from Server")

    def connect(self, addr: tuple[str, int] = (),  # type: ignore
                autoconnect: bool = False, timeout: float = 0.5) -> str:
        """Connects the client with a server.

        ...

        Connects the client either through an inputted address *(direct
        connect)* or tries addresses that knowingly are/were used by
        servers *(autoconnect)*. If an address holds a server, a
        registration protocol is carried out to ensue compatibility
        between client and server. After that a *receiving thread* is
        started to receive data from the *serversock*.

        ---
        Parameters
        ----------
        addr : tuple[str, int], optional
            Address (ip, port) of the server to connect to
        autoconnect : bool, optional
            Use 'known' server addresses to connect to
        timeout : float, optional
            Abandon connect attempt after n seconds

        ---
        Returns
        -------
        str : Returns one of the following states:
            - 'Connected'
            - 'Already connecting'
            - 'No Server on this address'
            - 'Server refused Connection'
            - 'Address is unsuited for client'
            - 'No IPs for autoconnect listed'
            - 'Timeout'

        ---
        See Also
        --------
        searchForServer : Searches for active server
        registration : Registration protocol
        recvServerData : Receiving thread for a connected socket

        ---
        Notes
        -----
        - Addresses of known servers for *autoconnect* can be gained
        with `searchForServer()` and are stored in `autoconnect_addrs`.
        - A receiving thread is a thread that receives and evaluates
        data on a connected socket.

        ---
        Examples
        --------
        >>> c.connect(autoconnect=True)

        >>> c.connect(('192.168.178.140', 4000))

        >>> c.connect(('192.168.178.140', 4001), True, 1.5)
        """

        # Preparation
        if not addr:
            addr = ('', -1)
        if self._connecting:
            self.statusInfo("Already connecting")
            return 'Already connecting'
        if len(self.autoconnect_addrs) == 0 and autoconnect \
        and addr == ('', -1):
            self.statusInfo("No IPs for autoconnect")
            return 'No IPs for autoconnect listed'

        if addr == ('', -1) and not autoconnect:
            self.warningInfo("No address for connect provided")
        if self.connected:
            self.disconnect()
        self._connecting = True
        self.clientsocks[addr[1]] = socket()  # User socket

        # Direct connect
        if addr != ('', -1):
            try:
                self.statusInfo(f"Connecting to {addr[0]}")
                self.clientsocks[addr[1]].settimeout(timeout)
                self.clientsocks[addr[1]].connect((addr[0], int(addr[1])))
                self.clientsocks[addr[1]].settimeout(None)
                self.connected_addr = addr
                self.connected = True
            except OSError:
                self.statusInfo("No server found")
                if autoconnect:
                    self.clientsocks[addr[1]].settimeout(None)
                else:
                    del self.clientsocks[addr[1]]
                    self.disconnect()
                    return 'No Server on this address'

        # Autoconnect
        if autoconnect and not self.connected:
            self.statusInfo("Starting autoconnect")
            for addr in self.autoconnect_addrs:
                Thread(
                    target=self._checkAddr,
                    args=(addr,),
                    name=f'checkAddr_{addr[0]}'
                ).start()

        # Wait for connection (or timeout)
        started = time()
        while not self.connected:
            if time() - started >= timeout:
                if autoconnect:
                    del self.clientsocks[addr[1]]
                self.disconnect()
                self.statusInfo(
                    f"Timeout({timeout} secs) while waiting for a connection")
                return 'Timeout'
            sleep(0.0001)

        # Connected but registering
        self.statusInfo(f"Connected with {self.connected_addr[0]} at "
                        + f"{self.connected_addr[1]}")
        try:
            self.registration()
        except (ConnectionError, ConnectionResetError, EOFError):
            self.statusInfo("Registration failed")
            self.disconnect()
            return 'Server refused Connection'
        except TimeoutError:
            self.statusInfo(
                f"Address {self.connected_addr} is unsuited for this client")
            self.disconnect()
            return 'Address is unsuited for client'
        self._connecttime = time()
        self._connecting = False

        if not [entry for entry in self.autoconnect_addrs \
                if entry is self.connected_addr]:
            self.autoconnect_addrs.append((
                self.connected_addr[0],
                self.connected_addr[1]))

        # Wait for maindatasock to get connected
        # (ensures that scripts can use the maindatasock)
        starttime = time()
        socknames = [sock[0] for sock in self.cl_serverdata['socks']]
        while len(self.clientsocks) == 1 and 'Maindata' in socknames:
            if time() - starttime > 1.5:
                self.warningInfo("Maindatasock did not get connected")
                break
        return 'Connected'

    def connectDatasock(self, addr: tuple[str, int],
                        recv_func: Callable = 'default'  # type: ignore
                        ) -> Optional[socket]:
        """Initiates a new socket and connects it to a serverdatasock.

        ...

        Connects a `socket` and warns if it couldn't get connected. The
        socket gets validated and the **recv_func** called as thread
        handles receiving and evaluating data from that socket.

        ---
        Parameters
        ----------
        addr : tuple[str, int]
            Address (ip, port) of a serverdatasock
        recv_func : Callable, optional
            Method that handles receiving data

        ---
        Returns
        -------
        socket : `socket` object of the new socket
        None : The socket couldn't get connected

        ---
        Notes
        -----
        - Some sockets (like maindatasock) get automatically connected
        with the client connecting to a server. This happens after the
        *registration* and is done by *clientcommands*.
        - The **recv_func** must be compatible with the data format sent
        by the server. This is only a problem if the server sends data
        on another way than with the inbuilt send-functions.

        ---
        Examples
        --------
        >>> c.connectDatasock(('192.168.178.140', 3999))
        <socket ...>

        >>> c.disconnect()
        >>> c.connectDatasock(('192.168.178.140', 3999))
        None
        """

        if not self.connected:
            self.warningInfo(
                "Client needs to be connected to create a datasocket")
            return None
        if addr[1] in self.clientsocks.keys():
            self.warningInfo(f"A socket is already connected to {addr}")
            return None
        if recv_func == 'default':
            recv_func = self.recvServerData
        new_datasock = socket()
        new_datasock.connect(addr)

        try:
            # Validate sockettype
            new_datasock.send('datasocket'.encode())
            new_datasock.settimeout(0.5)
            if new_datasock.recv(32).decode() != 'suited sockettype':
                raise TimeoutError
            new_datasock.settimeout(None)

            # Send identification to server
            new_datasock.send(dumps(
                self.clientsocks[self.connected_addr[1]].getsockname()))
        except (TimeoutError, ConnectionResetError):
            self.statusInfo(
                f"Address {addr} is unsuited for a datasocket")
            new_datasock.close()
            return None

        Thread(
            target=recv_func,
            args=(new_datasock,),
            name=f'Recv_Data{new_datasock.getpeername()[1]}'
        ).start()
        self.clientsocks[addr[1]] = new_datasock
        self.statusInfo(f"Connected new datasocket to port {addr[1]}")
        return new_datasock

    def _checkAddr(self, addr: tuple[str, int]):
        """Tries to connect a `socket` to an address.

        ...

       Simply connects a `socket` object to an address and handles
       connect success and failure. Used to speed up an *autoconnect* of
       `connect()`.

        ---
        Parameters
        ----------
        addr : tuple[str, int]
            Address (ip, port) to check

        ---
        See Also
        --------
        connect : Connects the client to a server

        ---
        Notes
        -----
        - This is not an equivalent to the `connect()`. method.
        - The *autoconnect* option of `connect()` tries to connect to an
        already known server address without entering the address again.
        """

        checksock = socket()
        try:
            if not self.connected and self._connecting:
                self.statusInfo(f"Trying to connect to {addr[0]} at {addr[1]}")
                checksock.settimeout(0.2)
                checksock.connect((addr[0], int(addr[1])))
                if not self.connected and self._connecting:
                    self.connected_addr = addr
                    self.connected = True
                    self.clientsocks[addr[1]] = checksock
                    self.clientsocks[addr[1]].settimeout(None)
            else:
                checksock.close()
        except OSError:
            del checksock

    def searchServers(self, ports: list[int] | tuple[int, ...],
                      ips: list[str] | tuple[str, ...] | str = 'locals',
                      only_one: bool = False, add_to_autoconnect: bool = True,
                      log_info: bool = False) -> list[tuple[str, int]]:
        """Searches for active servers in the same network.

        ...

        Uses the **ips** (or the machine ip by default) and **ports**
        and searches for active servers on any combination of those
        addresses. This happens by uses a modified `Client` as a
        *Serverfinder* which checks *serversocks* and ignores
        *datasocks* and addresses without compatible server. The found
        addresses can be returned and stored for *autoconnect* attempts.

        ---
        Parameters
        ----------
        ports : Iterable[int]
            Ports that get checked for servers
        ips : Iterable[str] | str, optional
            Search on these ip addresses
        only_one : bool, optional
            Return after the first server is found
        add_to_autoconnect: bool, optional
            Automatically save addresses for *autoconnect* attempts
        log_info : bool, optional
            Log information about tried addresses and found server

        ---
        Returns
        -------
        list[tuple[str, int]] : Addresses (ip, port) of found servers

        ---
        Notes
        -----
        -By default *(ips='locals')* the private local network is
        searched. This may take a few seconds to go though all ports on
        256 IP addresses. It is recommended to use the **ips** parameter
        to narrow the search range to only a few IPs.
        - With **add_to_autoconnect** the found server addresses will
        become "known addresses". When `connect(autoconnect=True)` is
        called the server tries to connect to any of these previously
        found addresses.
        - *serversocks* are the mainly used socket of servers and
        *datasocks* are secondary sockets for data transfer.

        ---
        Examples
        --------
        >>> # Two server are bound to port 4000 and 4001
        >>> c.searchForServer(range(4000, 4010), only_one=True)
        [('192.168.178.140', 4000)]

        >>> c.searchForServer(ports=[4000, 4001], ips=['192.168.178.140'])
        [('192.168.178.140', 4000), ('192.168.178.140', 4001)]

        >>> c.searchForServer((4000, 4001), log_info=True)
        Found Server on 192.168.178.140 at 4000  # In logfile
        Found Server on 192.168.178.140 at 4001
        [('192.168.178.140', 4000), ('192.168.178.140', 4001)]
        """

        if isinstance(ports, int):
            ports = [ports]
        if isinstance(ips, str):
            ips = [ips]

        # Thread that searches for servers on a certain port
        def searchPortOnAddress(for_ips, on_port):
            def mute(client, message): pass
            c = Client()
            c._conntype = 'SERVERFINDER'
            c.printInfo = mute.__get__(c, Client)
            c.statusInfo = mute.__get__(c, Client)
            c.warningInfo = mute.__get__(c, Client)
            c.errorInfo = mute.__get__(c, Client)
            for ip in for_ips:
                if only_one and len(found_servers) > 0:
                    return
                info = c.connect((ip, on_port), False, 0.01)  # May be to short
                if only_one and len(found_servers) > 0:
                    return
                if info == 'Server refused Connection':
                    found_servers.append((ip, on_port))
                    if log_info:
                        self.statusInfo(f"Found Server on {ip} at {on_port}")

        found_servers = []
        threads = []
        if isinstance(ips, str):
            ips = [ips]
        elif not isinstance(ips, list):
            ips = list(ips)
        if ips == ['locals']:
            ip_base = self.ip[::-1].split('.', 1)[1][::-1]
            ips = [f'{ip_base}.{e}' for e in range(256)]
        if log_info:
            self.statusInfo(
                "Searching for " + ("a server" if only_one else "servers")
                + f" on {len(ips)} {'IPs' if len(ips) > 1 else 'IP'}"
                + f" at {len(ports)} "
                + f"{'ports' if len(ports) > 1 else 'port'}.")

        for port in ports:
            threads.append(Thread(target=searchPortOnAddress,
                                            args=(ips, port,),
                                            name=f'Search_{port}'))
            threads[-1].start()

        for thread in threads:
            thread.join()
        if add_to_autoconnect:
            for addr in found_servers:
                if addr not in self.autoconnect_addrs:
                    self.autoconnect_addrs.append(addr)
        return found_servers

    def registration(self):
        """Check compatibility and exchange metadata when connecting.

        ...

        ---
        Raises
        ------
        TimeoutError : Unsuited sockettype (handled by `connect()`)
        ConnectionError : Large clientdata (handled by `connect()`)

        ---
        See Also
        --------
        connect : Connect the client to a server
        """

        sock = self.clientsocks[self.connected_addr[1]]

        # Validate sockettype
        sock.send('clientsocket'.encode())
        sock.settimeout(0.5)
        s = sock.recv(32).decode()
        if s != 'suited sockettype':
            raise TimeoutError
        sock.settimeout(None)

        # Check version
        sock.send(f'{self._conntype}|{Client.__version__}'.encode())

        # Exchange serverdata
        self.cl_serverdata = loads(sock.recv(4096))
        self.layer = self.cl_serverdata['layer'] + 1
        self._cl_sep = self.cl_serverdata['separator']
        self.cl_max_datasize = self.cl_serverdata['max_datasize']

        # Exchange clientdata
        binary_clientdata = dumps(self.getClientData())
        if len(binary_clientdata) > 4096:
            self.errorInfo(
                "Clientdata is larger than 4096 bytes and connect will fail")
            raise ConnectionError
        sock.send(binary_clientdata)

        # Set username
        self.username = sock.recv(
            self.cl_serverdata['max_username_length']).decode()

        # Start data receiver and inform server
        Thread(target=self.recvServerMessage,
                         name='Recv_Server'
        ).start()
        sock.send('continue'.encode())

    def recvServerMessage(self):
        """Receives data from the serversock.

        ...

        Essentially a wrapper for ´recvServerData´ that disconnects the
        whole client if the connection fails.

        ---
        See Also
        --------
        recvServerData : Receives and evaluates data from a socket
        """

        self.recvServerData(self.clientsocks[self.connected_addr[1]])
        if self.connected:
            self.disconnect()

    def recvServerData(self, sock: socket):
        """Receives and evaluates data on a socket.

        ...

        The default receiving method for receiving data from any socket
        of the server. Receives data *packets* and recombines them.
        Complete data transmissions get evaluated for for
        *clientcommands*, *requestables* and simple text messages.
        Resets and deletes the socket if the connection fails.

        ---
        Parameters
        ----------
        sock : socket
            Socket to receive data from

        ---
        See Also
        --------
        recvServerMessage : Receives data through the clientsock

        ---
        Notes
        -----
        - The server splits large data in chunks *(packets)* that
        get transmitted one by one and recombined here.
        - *Clientcommands* are code snippets that can be called through
        the server.
        - *requestables* allow the server to request data from the
        client.
        """

        buffer = b''
        data_packets = {}  # Stores packets until data is complete
        port = sock.getpeername()[1]
        separator = self._cl_sep.encode()

        try:
            while self.connected:
                buffer += sock.recv(self.cl_max_datasize)
                if len(buffer) > self.cl_max_datasize * 16:
                    self.warningInfo(f"Receiving buffer for socket {port} "
                                     + "holds a lot of bytes")
                if len(data_packets) > 16:
                    self.warningInfo(f"Socket on {port} has many uncompleted "
                                     + "transmissions packets")

                # Extract packets in buffer
                while separator in buffer:
                    packet, buffer = buffer.split(separator, 1)
                    try:
                        packet = loads(packet)
                    except UnpicklingError:
                        self.warningInfo(f"A received packet on port '{port}' "
                                         + "cannot be decoded")
                        continue

                    # Packet is part of larger data
                    if packet[2] > 0:
                        if not packet[0] in data_packets:
                            data_packets[packet[0]] = packet[3]
                            continue
                        data_packets[packet[0]] += packet[3]
                        if not packet[1] == packet[2]:
                            continue
                        packet[3] = data_packets[packet[0]]
                        del data_packets[packet[0]]

                    # Evaluate packet/complete data
                    packet[3] = packet[3].replace(
                        eval("'<$-' + '$SEP$' + '-$>'").encode(),
                        self._cl_sep.encode())
                    try:
                        data = loads(packet[3])
                    except UnpicklingError:
                        self.warningInfo(f"Received data on port '{port}' is "
                                         + "unreadable and will be ignored")
                        continue

                    # Process request
                    if isinstance(data, list) and data[0] == '<$REQUEST$>':
                        if data[1] == 'request':  # Requested by server
                            if not data[3] in self.cl_requestables:
                                self.sendData(sock, ['<$REQUEST$>', 'answer',
                                              data[2], None])
                                continue
                            requesteddata = self.cl_requestables.get(data[3])
                            if callable(requesteddata):
                                requesteddata = requesteddata()
                            self.sendData(sock, ['<$REQUEST$>', 'answer',
                                                 data[2], requesteddata])
                        elif data[1] == 'answer':  # Answer for client request
                            if data[2] in self._open_requests:
                                self._open_requests[data[2]] = data[3]
                            else:
                                self.warningInfo(
                                    "Received requested data after timeout")
                        else:
                            self.errorInfo(
                                f"Invalid request phrase '{data[1]}'")

                    # Process clientcommand
                    elif isinstance(data, list) and data[0] == '<$COMMAND$>':
                        self.execClientCommand(sock, data[1], data[2])

                    # Display on console if data is text
                    elif isinstance(data, str):
                        if self.getPort(sock) == self.connected_addr[1]:
                            sender = (
                                f"\033[0;1m[\033[4;53m"
                                + f"{datetime.now().strftime('%H:%M:%S')}"
                                + "\033[0m]\033[3m"
                                + f"{self.cl_serverdata['servername']}"
                                + "\033[0m> ")
                        else:
                            sender = (
                                f"\033[0;1m[\033[4;53m"
                                + f"{datetime.now().strftime('%H:%M:%S')}"
                                + f"\033[0m]\033[3m"
                                + f"{self.cl_serverdata['servername']}"
                                + f"\033[2m({sock.getpeername()[1]})"
                                + "\033[0m> ")
                        self.printInfo(data, sender)
                    else:
                        self.warningInfo("Received unprocessable data at a"
                                         + f"datasock connected at port"
                                         + str(sock.getpeername()[1]))
            raise ConnectionResetError
        except (ConnectionResetError, ConnectionAbortedError, OSError):
            self.statusInfo(f"Lost connection to socket at {port}")
        finally:
            sock.close()
            try:
                del self.clientsocks[self.getPort(sock)]
            except ValueError:  # In case a disconnect call removed the socket
                pass

    def sendData(self, sock: socket, data: Any):
        """Sends data through a socket to a Server.

        ...

        The passed **data** gets binary encoded and embedded with
        metadata of that transmission. If the data is to large for one
        transmission it gets split into multiple *packets* and send one
        by one. The server recombines the packets.

        *NOTE: The receiving **sock** must use the `recvClientData()`
        receiving Function (recvFunc) for this to work. Serversocks with
        a custom recvFunc need a custom send Function!.*

        ***Not to be confused with `network.Server.sendDataTo()`!***

        ---
        Parameters
        ----------
        sock : socket
            Socket that transmits data
        data : object
            Python object that gets transmitted

        ---
        See Also
        --------
        sendServerMessage : Sends a text (can include a servercommand)
        sendRequest : Requests data from the server

        ---
        Notes
        -----
        - Multiple *packets* are only needed if the binary data exceeds
        the *cl_max_datasize* value (that gets set through a server).
        - The metadata/header of a *packet* has a size of around 80
        bytes.

        ---
        Examples
        --------
        >>> c.sendData(c._clientsocks[4000], "Hello")

        >>> c.sendData(c._clientsocks[4000], [42, "str", False])
        """

        if not self.connected:
            self.warningInfo("No connection to send data to")
            return
        transmission_id = self._generateTransmissionID()
        try:
            data = dumps(data)
        except PicklingError:
            self.errorInfo("Transmitting data cannot be converted to bytes")
            return
        # Data can't contain the original separator to be usable
        data = data.replace(self._cl_sep.encode(),
                            eval("'<$-' + '$SEP$' + '-$>'").encode())
        # Estimate size of packet metadata (less than 100 bytes)
        header_size = len(dumps([
            transmission_id, 0, int(len(data)/self.cl_max_datasize),
            b'']) + self._cl_sep.encode()) + 10
        data_per_packet = self.cl_max_datasize-header_size
        needed_packets = int(len(data)/data_per_packet) + 1

        # Send packets
        try:
            for pack in range(needed_packets):
                sock.send(
                    dumps([transmission_id, pack, needed_packets - 1,
                          data[pack*data_per_packet:(pack+1)*data_per_packet]])
                    + self._cl_sep.encode())
        except Exception as e:
            self.warningInfo(
                f"Senderror: {str(e)[:35]}... by passing {str(e)[:30]}....")
            self.logEvent(f"occurred error: {e}")

    def sendMsg(self, message: str):
        """Sends a string to a server.

        ...

        ***Not to be confused with `network.Server.sendMsgTo()`!***

        ---
        Parameters
        ----------
        message : str
            Message that gets transmitted

        ---
        See Also
        --------
        sendData : Sends data to the server

        ---
        Examples
        --------
        >>> c.sendMsg("Hello")

        >>> msg = input("Enter message:")
        >>> c.sendMsg(msg)
        """

        if message == "":
            return
        self.sendData(self.clientsocks[self.connected_addr[1]], message)

    def sendRequest(self, sock: socket, request: str,
                      timeout: Optional[float] = 1.0) -> Optional[object]:
        """Requests data from a server.

        ...

        Sends a data request with an identification key to a sock. If
        the server has a matching *requestable*, it sends the requested
        data together with the identification key back to the socket.

        ***Not to be confused with `network.Server.sendRequestTo()`!***

        ---
        Parameters
        ----------
        sock : socket
            Socket that sends the request
        request : str
            Name of a server requestable
        timeout : float | None, optional
            Abort the request if no data is returned after n seconds.

        ---
        Returns
        -------
        object : Requested data
        None : If timeout or not connected to a server

        ---
        See Also
        --------
        sendData : Sends data to the server

        ---
        Notes
        -----
        - The `recvServerData()` thread *(receiving thread)* for the
        socket will receive the data and store it in the *_open_requests*
        dictionary.
        - Available *server requestables* are defined by the server.
        - *Requestables* should be written in uppercase but this is not
        enforced.

        ---
        Examples
        --------
        >>> c.sendRequest(_clientsocks[4000], 'SERVERDATA')
        {...}

        >>> c.sendRequest(_clientsocks[4000], 'NON_EXISTENT')
        No requestable 'NON_EXISTENT'

        >>> c.disconnect()
        >>> c.sendRequest(socket(), 'REQUEST')
        None
        """

        if not self.connected:
            return None
        request = request
        key = self._generateRequestID()
        self._open_requests[key] = request
        self.sendData(sock, ['<$REQUEST$>', 'request', key, request])
        starttime = time()
        while self.connected and self._open_requests[key] == request:
            if timeout is not None \
            and time() - starttime >= timeout:
                self.warningInfo(
                    f"Request for '{request}' did not receive data")
                return None
        data = self._open_requests[key]
        del self._open_requests[key]
        return data

    # ----------------+
    # Getter function |
    # ----------------+

    def getPort(self, sock: socket) -> int:
        """Gets the port a socket is/was connected to.

        ...

        If the sock is still connected, the *raddr* of *socket*
        is used. Otherwise the key of *_clientsocks* is used, which also
        represents the port.

        ---
        Parameters
        ----------
        sock: socket
            Socket which connected port is needed

        ---
        Returns
        -------
        int : Port the **sock** is connected to
        """

        try:
            return sock.getpeername()[1]
        except OSError:
            return list(self.clientsocks.keys())[list(
                self.clientsocks.values()).index(sock)]

    def getClientData(self) -> dict[str, object]:
        """Gets metadata of the client.

        ...

        ---
        Returns
        -------
        dict[str, object] : Different stats of the client
        """

        return {'description': self.description,
                'username': self.username,
                'client_version': Client.__version__,
                'commands': list(self.cl_commands.keys()),
                'requestables': list(self.cl_requestables.keys())}

    @staticmethod
    def _generateTransmissionID() -> str:
        """Generates a unique id for packages of transmitted data.

        ...

        ---
        Returns
        -------
        str : new id
        """

        return str(uuid4())

    @staticmethod
    def _generateRequestID() -> str:
        """Generates a unique key to identify requests.

        ...

        ---
        Returns
        -------
        str : generated key
        """

        return str(uuid4())

    def __str__(self) -> str:
        """Values returned when converting to string.

        ...

        ---
        Returns
        -------
        str : `Client` object formatted to string
        """

        returned = f"Client ({self.username}),"
        if self.connected:
            returned += f"connected, connected_addr={self.connected_addr}"
        else:
            returned += "not connected"
        return f"<{returned}>"

    # ---------------------+
    # Displaying functions |
    # ---------------------+

    def printInfo(self, message: str, sender: str = ""):
        """Outputs a server message and logs the event.

        ...

        The name of the server is added as a prefix.

        ---
        Parameters
        ----------
        message : str
            Text that gets outputted
        sender : str, optional
            The name of the sender (servername)

        ---
        See Also
        --------
        statusInfo : Outputs a state of the client
        warningInfo : Outputs a warning
        errorInfo : Outputs an error
        logEvent : Logs an events

        ---
        Notes
        -----
        - The message can be colored if *ANSI* codes are allowed.
        """

        if not sender:
            message = f"\033[1;4m{sender}\033[0;1m\033[0m{message}"
        if not self._ansi:
            message = compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])').sub(
                '', message)
        print(message)
        self.logEvent(message)

    def statusInfo(self, status: str):
        """Outputs a state of the client and logs the event.

        ...

        Parameters
        ----------
        status : str
            Status text that gets outputted

        ---
        See Also
        --------
        printInfo : Outputs a server message
        warningInfo : Outputs a warning
        errorInfo : Outputs an error
        logEvent : Logs an event

        ---
        Notes
        -----
        - If *ANSI* codes are allowed the status will be displayed gray.
        """

        if self._ansi:
            print(f"\033[38;5;243m{status}\033[0m")
        else:
            status = compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])').sub(
                '', status)
            print(status)
        self.logEvent(f"STATUS: {status}")

    def warningInfo(self, warning: str):
        """Outputs a warning and logs the event.

        ...

        Parameters
        ----------
        warning : str
            Warning Information that gets outputted

        ---
        See Also
        --------
        printInfo : Outputs a server message
        statusInfo : Outputs a state of the client
        errorInfo : Outputs an error
        logEvent : Logs an event

        ---
        Notes
        -----
        - If *ANSI* formatting is allowed, the warning will be displayed
        orange.
        """

        if self._ansi:
            print("\033[38;5;214m\033[1;4mWAR:\033[0;1m\033[38;5;214m " + \
                  warning + "\033[0m")
        else:
            warning = compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])').sub(
                '', warning)
            print(f"WAR: {warning}")
        self.logEvent(f"WARNING: {warning}")

    def errorInfo(self, error: str):
        """Outputs an error and logs the event.

        ...

        ---
        Parameters
        ----------
        error : str
            Error information that gets outputted

        ---
        See Also
        --------
        printInfo : Outputs a server message
        statusInfo : Outputs a state of the client
        warningInfo : Outputs a warning
        logEvent : Logs an events

        ---
        Notes
        -----
        - If *ANSI* formatting is allowed, the error message will be
        colored red.

        """

        if self._ansi:
            print(f"\033[91;1;4mERR:\033[0;1;91m {error}\033[0m")
        else:
            error = compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])').sub(
                '', error)
            print(f"ERR: {error}")
        self.logEvent(f"ERROR: {error}")

    def logEvent(self, event: str):
        """Saves events and writes them into a logfile (if available).

        ...

        ---
        Parameters
        ---------
        event : str
            Event information that gets stored

        ---
        See Also
        --------
        printInfo : Outputs a server message
        statusInfo : Outputs a state of the client
        warningInfo : Outputs a warning
        errorInfo : Outputs an error
        """

        event = compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])').sub(
                '', event)
        event = f"{datetime.now().strftime('%H:%M:%S:%f')}>  {event}\n"
        self._log.append(event)
        if self.logfile != "":
            with open(self.logfile, 'a') as log:
                log.write(event)
        # Warn about log size
        if len(self._log) % 10_000 == 0 and len(self._log) > 200_000:
            if self.logfile != "":
                self._log = []
                self.statusInfo(
                    f"Clearing internal log (size: {len(self._log)}) since "
                    + f"events get stored to '{self.logfile}'")
            else:
                self.warningInfo(
                    "Log holds many entries. Consider storing to a file.")


class Server:
    """Allows connections with clients and provides interaction tools.

    ...

    The server binds itself to an address when started. The socket on
    that address is the mainly used socket of the server, referred to as
    *serversock*. It is used for user inputs on clients. Additionally,
    the server can have multiple *datasocks* that are used for custom
    data transmissions. The *maindatasock* can be initiated with server
    start and is used to relive the *serversock*. New clients can only
    connect to the *serversock*. They get registered to ensure
    compatibility with the server and then passed to a *Recv* threads,
    that receives and evaluates the data clients send. The server
    provides *servercommands* and *serverrequestables* that allow
    clients to execute predefined scripts and request data from the
    server.

    When extending the Server class, all arguments of the new class
    constructor must be passes to the Server constructor.

    ---
    Attributes
    ----------
    addr : tuple
        Ip and port of the server address
        [ip:str, port:int]
    adminkey : str
        Password to gain admin permissions
    conns : dict
        All connected clients and their metadata
        dict[id:str, dict[properties:str, data:Any]]
    description : str
        Short description about the server
    layer : int
        Depth layer in a network
    logfile : str
        Filename of a log file that stores all events
    preferredport : str
        Allowed ports to bind the server to
    preferreddataport : str
        Allowed ports to bind datasocks to
    se_commands : dict
        Data of servercommands
        dict[name:str, tuple[list[func:Callable, call_as_thread:bool,
            needed_permissions:list[str], args:list[str],
            optional_args:list[str], repeatable_param:str, desc:str,
            category:str]]]
    se_max_datasize : int
        Maximum bytes received or sent at once for any socket
    se_requestables : dict
        Data that can be requested by clients
        dict[name:str, data:object]
    se_running : bool
        Server is running
    se_sep : str
        Separator used to identify the end of transmitted bytes
    serversocks : dict
        All socks and their metadata
        dict[name:str, list[socket, connect_new_clients:bool,
            show_info:bool]]
    services : list
        Metadata of initialized services
        list[list[Callable, bool, bool]]
    services_active : bool
        Services are running
    starttime : float
        Server starttime
    username : str
        Name of the server
    _log : list[str]
        Saves all occurred events
    _min_username_length : int
        Minimum characters a username can have
    _max_username_length : int
        Maximum characters a username can have
    _open_requests : dict
        Unanswered requests to get data from a client socket
        dict[id:str, request_or_data:Any]
    _restricted_usernames : list[str]
        Names that are not allowed as usernames

    ---
    Structure of complex attributes
    -------------------------------
    conns[clientid: str] -> dict[str, Any] with:
        - 'name': str
        - 'socks: dict[int, socket]
        - 'isserver': bool
        - 'clientdata': dict[str, Any]
        - 'permissions': list[str]
        - 'muted': bool
        - 'connecttime': float
        - 'ping': float
        - 'data': dict[str, Any]

    serversocks[name: str] -> list[socket, bool, bool] with indexes:
        0. Socket: socket
        1. Connect new clients: bool
        2. Show info: bool

    services[name: str] -> list[Callable, bool, bool] with indexes:
        0. Function: Callable
        1. Call ad thread: bool
        2. Enabled: bool

    se_commands[name: str] -> list with indexes:
        0. Function: Callable
        1. Call as thread: bool
        2. Needed permissions: list
        3. args: list
        4. Optional args: list
        5. Repeatable arg: str
        6. Description: str
        7. Command category: str

    ---
    Servercommands
    --------------
    *([o]: optional argument, [r]: repeatable argument)*
    - s.closedatasock(serversockname[r])
    - s.restart()
    - s.services(enable, service_name[o])
    - s.services_info()
    - s.setadminkey(new_key)
    - s.shutdown()
    - s.storelog()
    - s.attributes()
    - s.errortrace()
    - s.getadminkey()
    - s.help(servercommand[o][r])
    - s.info(username[o][r])
    - s.listsocks()
    - s.listthreads()
    - s.changename(newname, clientname[o])
    - s.connectto(ip, port[o])
    - s.getadmin(adminkey[o])
    - s.getrights(permission[r])
    - s.kickip(ip[r])
    - s.kickuser(username[r])
    - s.mute(username[r])
    - s.ping()
    - s.removeadmin(username[o][r])
    - s.removerights(permission[r])
    - s.unmute(username[r])

    ---
    Serverrequestables
    ------------------
    - SERVERDATA

    ---
    Notes
    -----
    - Server sockets that are bound to an address and receive data
    from a client are referred to as *(server-/data-)socks*.
    - Server should be bound to ports 4000 and higher
    - Datasockets should be bound to port 3999 and lower
    - A low se_max_datasize (<~200) significantly decreases performance.
    - A muted client can't send anything (data, msg, command or request)
    to the server but it also can't answer requests by the server
    meaning data from a muted client may be outdated.

    ---
    Examples
    --------
    >>> s = Server()
    >>> s.startServer()
    >>> s.newDataSock('LargeDatasock', recvFunc=s.recvClientData)
    >>> id = s.getIDof(username='client1')
    >>> s.sendMsgTo(id, 'Hello')
    >>> s.sendCommandTo(id, 'DISCONNECT')
    >>> s.shutdownServer()
    """

    __version__ = '7.43.162'

    def __init__(self, servername: str = 'server', description: str = "None",
                 adminkey: str = '', max_datasize: int = 1024,
                 preferredport: int | str | Iterable[int]=  '>4000',
                 preferreddataport: int | str | Iterable[int] = '<3999',
                 logfile: str = '', ansi: bool = True, *args, **kwargs):
        """...

        ---
        Parameters
        ----------
        servername : str, optional
            Name of the server
        description : str, optional
            Short information text about the server
        adminkey : str, optional
            Password for admin permissions
        max_datasize : int, optional
            Maximum bytes of one transmission
        preferredport : int | str | Iterable[int], optional
            Allowed ports to bind the server to
        preferreddataport : int | str | Iterable[int], optional
            Allowed ports to bind datasocks to
        logfile : str, optional
            Path to file that stores all events
        ansi : bool, optional
            Allow *ANSI* text formatting

        ---
        Raises
        ------
        ValueError : *max_datasize* too small

        ---
        Notes
        -----
        - **Preferred(data)port** should be used with an integer or
        iterable if only certain ports are allowed to bind sockets to.
        Use a string number beginning with '>'/'<' if a certain port and
        all available ports above/below are allowed.
        - Data that exceeds the **max_datasize** bytes limit, get
        splitted into multiple *packets* and transmitted one by one.
        - *Datasocks* get bound to the first free port lower than
        **highest_dataport**.
        - If the default **adminkey** is used, every connection gets
        admin permissions when connecting.
        - By default no new **logfile** will be created.
        - **args** and **kwargs** must contain arguments of child
        object. Otherwise restarting the server object would only create
        a default `Server` instance.
        """

        self._init_args = args
        self._init_kwargs = locals() | kwargs  # type: ignore
        del self._init_kwargs['self']
        del self._init_kwargs['args']
        del self._init_kwargs['kwargs']

        self.username = servername  # This will be the username of a SubServer
        self.preferredport = preferredport
        self.preferreddataport = preferreddataport
        self.se_max_datasize = max_datasize
        self.adminkey = adminkey
        self.description = description
        self.logfile = logfile
        self._ansi = ansi

        self._log: list[str] = []
        self.services: dict[str, list[Callable | bool]] = {}
        self.serversocks: dict[str, tuple[socket, bool, bool]] = {}
        self.conns: dict[str, dict[str, Any]] = {}
        self.se_commands: dict[str, tuple[Callable, bool, list[str], list[str],
            list[str], str, str, str]] = {}
        self._open_requests: dict[str, Any] = {}
        self.se_requestables: dict[str, object] = {}
        self._restricted_usernames: list[str] = ['command' 'commands',
            'servercommand', 'servercommands', 'info', 'requestables',
            'services', 'server', 'subserver', 'mainserver', 'higher']
        self.addr: tuple[str, int] = ('', -1)
        self._min_username_length: int = 2
        self._max_username_length: int = 16
        self._starttime: float = -1.0
        self.layer: int = 0
        self.se_running: bool = False
        self.services_active: bool = False
        self._se_sep: str = eval("'<$' + 'SEP' + '$>'")

        # Fixes ANSI formatting bug on windows
        if self._ansi: system("")

        Server._initServices(self)
        Server._initServercommands(self)
        Server._initServerRequestables(self)

        if self.logfile != '':
            self.statusInfo(f"Storing logfile at '{self.logfile}'")
            open(self.logfile, 'w').close()

        # Initialization checks
        if max_datasize < 100:
            raise ValueError("Maximum data size must be at least 100 (bytes)")
        if isinstance(self.preferredport, str) \
        and not self.preferredport.isnumeric():
            try:
                int(self.preferredport[1:])
                if self.preferredport[0] not in ['>', '<', '=']:
                    raise ValueError
            except ValueError:
                raise ValueError(
                    "The preferred port can only contain the non-numerics "
                    + "'<', '>' or '=' at the FIRST position")
        if isinstance(self.preferreddataport, str) \
        and not self.preferreddataport.isnumeric():
            try:
                int(self.preferreddataport[1:])
                if self.preferreddataport[0] not in ['>', '<', '=']:
                    raise ValueError
            except ValueError:
                raise ValueError(
                    "The preferred data port can only contain the non-numerics"
                    + " '<', '>' or '=' at the FIRST position")
        self.logEvent(f"Server ({Server.__version__}) loaded")

    def startServer(self, port: int | str | Iterable[int] = 'preferred',
                    dataport: int | str | Iterable = 'preferred',
                    maindatasock: bool = False, services: bool = True):
        """Binds and starts the server.

        ...

        Binds the serversock to an available allowed port in **port**.
        After this clients will be able to connect to the server. If
        needed, the maindatasock for background interactions can be
        initialized and bound to a port in **dataport**. Additionally
        services, for repetitive tasks like data synchronization can be
        activated.

        ---
        Parameters
        ----------
        port : int | str | Iterable[int], optional
            Allowed ports to bind the serversock to
        dataport :  int | str | Iterable[int], optional
            Allowed ports to bind datasocks to
        maindatasock : bool, optional
            Initiate the Maindatasock
        services : bool, optional
            Start services routine

        ---
        Raises
        ------
        OSError : Can't bind the server to any **port**

        ---
        See Also
        --------
        newDataSock : Create a new datasock
        shutdownServer : Shut the server down
        restartServer : Restarts the server
        servicesController : Manages services

        ---
        Notes
        -----
        - By default all sockets of the server will be bound to
        preferred ports specified with the server initialization.
        - **(data)port** will not overwrite the preferred ports of the
        server.
        - The *maindatasock* is not necessary but can reduce the
        workload on the *serversock*.
        - Services and *maindatasock* can also be initiated after the
        server start.

        ---
        Examples
        --------
        >>> Server('server1').startServer()

        >>> Server('server2').startServer(4001, True, True)

        >>> Server('server3').startServer(
        ...     port='>4000',  # binds to 4000 or port above
        ...     dataport='<3999')
        """

        if self.se_running:
            self.warningInfo("Server is already running")
            return
        self.logEvent("Starting server")

        # parse useable (data)ports
        if port == 'preferred':
            port = self.preferredport
        self.preferredport = port
        port = self._parse_port_expression(port)
        if dataport == 'preferred':
            dataport = self.preferreddataport
        self.preferreddataport = dataport
        dataport = self._parse_port_expression(dataport)

        # Gain ip address
        s = socket(AF_INET, SOCK_DGRAM)
        s.connect(('1.1.1.1', 1))
        ip = s.getsockname()[0]
        s.close()
        del s

        # Connect serversock
        self.logEvent("Binding sockets")
        serversock = socket(AF_INET, SOCK_STREAM)
        for p in port:
            if p < 0 or p > 65535:
                raise OSError(
                    "Can't start server, all allowed/available ports are used")
            try:
                serversock.bind((ip, p))
                self.addr = (ip, int(p))
                self.statusInfo(f"Serversock bound to {self.addr[1]}")
                break
            except OSError:
                self.logEvent(f"port {p} is used")
        else:
            self.errorInfo("Can't bind server to any preferred port")
            raise OSError(
                "Can't start server, all preferred/allowed ports are used")

        serversock.listen(10)
        self.se_running = True
        self._starttime = time()
        self.serversocks['Serversock'] = (serversock, True, True)
        Thread(target=self._acceptClient, name=f'Connect_{self.addr[1]}'
        ).start()
        self.statusInfo(f"Server is running at {self.addr}")
        if maindatasock:
            maindata = self.bindMaindataSock(dataport)
            if maindata is None:
                self.errorInfo("Maindatasock could not get bound")
        if services:
            Thread(target=self.servicesController, name='Service'
            ).start()

    def restartServer(self):
        """Restarts the server.

        ...

        Disconnects all clients and unbinds socks, then creates a new
        logfile (if one is used). After that all attributes get reset
        to the initial values and the server starts again.

        ---
        See Also
        --------
        shutdownServer : Disconnect clients and unbind socks
        startServer : Starts the server

        ---
        Examples
        --------
        >>> s.startServer()
        >>> s.restartServer()
        """

        self.shutdownServer()
        self.statusInfo("Restarting Server")
        if self.logfile != '':
            temp = self.logfile.split('.', 1)
            if len(temp) == 2:
                self.logfile = f'{temp[0]}_restart{temp[1]}'
            else:
                self.logfile += '_restart'

        try:
            self = self.__class__(*self._init_args, **self._init_kwargs)
        except Exception as e:
            self.errorInfo("Failed to restart server object"
                           + f"'{self.__class__}' due to: {str(e)}")
            self.warningInfo("Binding server with previous settings")
        self.startServer()

    def shutdownServer(self):
        """Disconnects all users, unbinds socks and ends services.

        ...

        ---
        See Also
        --------
        startServer : Starts the server
        restartServer : Restarts the server

        ---
        Examples
        --------
        >>> s = Server("server")
        >>> s.startServer()
        >>> s.shutdownServer()
        """

        if not self.se_running:
            self.warningInfo(
                "Server is not running, shutdown resets attributes")
        self.statusInfo("Shutting Server down")
        self.statusInfo("Stopping services")
        self.services_active = False
        self.statusInfo("Disconnecting all users")
        self.se_running = False
        self.services_active = False
        for clientid in [key for key in self.conns]:
            self.sendCommandTo(self.mainSocketof(clientid),  # type: ignore
                               "disconnect")
            try:
               self.mainSocketof(clientid).close()  # type: ignore
            # Client has disconnected
            except (ValueError, KeyError, AttributeError):
                pass
        while len(self.conns) > 0:
            sleep(0.001)
        self.statusInfo("Unbinding all sockets")
        [self.closeDataSock(name) for name in self.serversocks.copy()]
        started = time()
        while len(self.serversocks) > 0:
            sleep(0.001)
            if time() - started > 1:
                self.errorInfo("Serversockets are not closing correctly")
                return
        self.statusInfo("Server is inactive")

    def bindMaindataSock(self, dataport: int | str | Iterable = 'preferred'):
        """Initiates the maindatasock.

        ...

        ---
        Parameters
        ----------
        dataport : int | str | Iterable, optional
            Possible ports to bind the maindatasock to

        ---
        Returns
        -------
        socket : Socket object of the maindatasock
        None : Maindatasock already exists or could not be bound

        ---
        See Also
        --------
        startServer : Starts the server and can bind the maindatasock
        newDataSock : Initiates a new datasock

        ---
        Notes
        -----
        - By default **dataport** uses the preferred ports set with
        server initialization.
        - The first available port in **dataport** is used.
        """

        if dataport == 'preferred':
            dataport = self.preferreddataport
        if 'Maindata' in self.serversocks:
            self.warningInfo("The maindatasock is already initiated")
            return None
        maindatasock = self.newDataSock('Maindata', self.recvClientData,
            dataport=dataport, connect_clients=self.conns.keys(), #type: ignore
            connect_new_clients=True, show_info=True)
        if maindatasock is None:
            self.errorInfo("Maindatasock could not get bound")
        return maindatasock

    def newDataSock(self, sockname: str,
                    recvFunc: Callable = 'default',  # type: ignore
                    dataport: int | str | Iterable = 'preferred',
                    connect_clients: list[str] | str = [],
                    connect_new_clients: bool = False,
                    show_info: bool = False) -> Optional[socket]:
        """Initiates a new datasock for data transmission.

        ...

        Binds a socket to an allowed, unused port. A thread is started,
        that accepts new connections for this datasock and passes them
        to the **recvFunc** that receives data for that socket on this
        datasock.

        ---
        Parameters
        ----------
        sockname : str
            Name of the new datasock
        recvFunc : Callable, optional
            Function that receives and processes data from a socket
        dataport : int | str | Iterable, optional
            Allowed port(s) to bind the serversock to
        connect_clients : list[str] | str, optional
            Connect the new datasock with these clientids
        connect_new_clients: bool, optional
            New connected clients get also connected to this datasock
        show_info : bool, optional

        ---
        Returns
        -------
        socket : The created datasock
        None : If no port is available

        ---
        Raises
        ------
        NameError : Sockname is already used

        ---
        See Also
        --------
        closeDataSock : Closes a datasocket
        recvThreadWrapper : Wrapper Function for recv Function/Threads
        recvClientData : Default **recvFunc**/recv Thread

        ---
        Notes
        -----
        -By default **allowed_ports** will use the *preferreddataport*
        set with server initialization.
        -As receiving Functions (**recvFunc**) the `recvClientData()`
        function can be used. It handles requestables, text and commands
        but other data(types) are ignored. In this case a custom
        recvFunc must be build. For this see the examples in the
        project repository and the `recvThreadWrapper()`.
        - Information of the datasock is added to the **serversocks**
        dict.

        ---
        Examples
        --------
        >>> s.createDatasock('datasock_1', s.recvClientData, 3999,
        ...                show_info=True)
        <socket ...>

        >>> s.createDatasock('datasock_2', s.recvClientData, [3999, 3997],
        ...                connect_new_clients=True)
        datasock_3 Datasock bound to 3997
        <socket ...>

        >>> # Connect every existing and future client to this datasock
        >>> s.createDatasock('datasock_3', s.recvClientData, '<3998',
        ...                connect_clients=s.conns.keys(),
                           connect_new_clients=True,
        ...                show_info=True)
        datasock_3 Datasock bound to 3998
        <socket ...>
        """

        # Preparations
        if self.getSockData(sockname) is not None:
            self.errorInfo(f"A datasock '{sockname}' already exists")
            raise NameError(f"A datasock '{sockname}' already exists")
        if recvFunc == 'default':
            recvFunc = self.recvClientData
        if isinstance(connect_clients, str):
            connect_clients = [connect_clients]
        if dataport == 'preferred':
            port = self.preferreddataport
        datasock = socket(AF_INET, SOCK_STREAM)
        maindatasock_port = self.getMainDataPort()

        # Bind sock
        for try_port in self._parse_port_expression(dataport):
            if try_port < 0 or try_port > 65535:
                self.errorInfo(
                    f"No ports available for datasock '{sockname}'")
                return None
            try:
                datasock.bind((self.addr[0], try_port))
                self.statusInfo(f"{sockname} Datasock bound to {try_port}")
                break
            except OSError:
                pass
        else:
            self.errorInfo(
                f"Can't bind datasock '{sockname}' to any allowed port")
            return None

        datasock.listen(10)
        self.serversocks[sockname] = (datasock, connect_new_clients, show_info)
        sockaddr = datasock.getsockname()
        Thread(
            target=self._acceptSocket,
            args=(datasock, recvFunc,),
            kwargs=dict(show_info=show_info),
            name=f'Connect_{sockaddr[1]}'
        ).start()

        # Connect clients in list
        for clientid in tuple(connect_clients):
            try:
                self.sendCommandTo(
                    self.conns[clientid]['socks'][maindatasock_port],
                    'newdatasock',
                    [sockaddr])
            except KeyError:
                self.warningInfo("Could not connect a clientid to new"
                                 + f" datasocket '{sockname}'")
        return datasock

    def closeDataSock(self, datasock: str):
        """Disconnects clientsockets and unbinds the datasock.

        ...

        ---
        Parameters
        ----------
        datasock : str
            Datasock name

        ---
        See Also
        --------
        createDatasock : Creates a new datasock

        ---
        Examples
        --------
        >>> s.newDataSock('datasock_1', recvClientData)
        >>> s.closeDataSock('datasock_1')
        """

        port = self.serversocks[datasock][0].getsockname()[1]
        self.statusInfo(f"Closing datasock '{datasock}' at {port}")

        # Disconnect all clientsocks
        for clientid in self.conns:
            if port in self.conns[clientid]['socks']:
                self.getSocketof(clientid, port).close()

        # Close and remove serversock
        self.serversocks[datasock][0].close()
        del self.serversocks[datasock]

    # -----------------------------+
    # Connect and interact methods |
    # -----------------------------+

    def _acceptClient(self):
        """Awaits a new client connecting to the serversock.

        ...

        Accepts new clients connecting to the serversock
        (`socket.accept()`) while the server is running. New connected
        sockets get passed to a registration thread.

        ---
        See Also
        --------
        registerClient : registers a new client
        acceptSock : Allows clients to connect datasockets
        """

        sock = self.serversocks['Serversock'][0]
        while self.se_running:
            client, (ip, port) = None, (None, None)
            try:
                try:
                    client, (ip, port) = sock.accept()
                except OSError:  # The server gets shut down
                    return
                if self.se_running:
                    self.logEvent(f"New connection with {ip}")
                    Thread(
                        target=self._registrateClient,
                        args=(client,),
                        name=(f'Recv_{str(sock.getsockname()[1])}_'
                              + ip.split('.')[-1])
                    ).start()

            except (OSError, IndexError):  # Client closed socket
                if self.se_running:
                    self.logEvent(f"Lost connection with a new client({ip}) "
                                   + "on The Serversocket"
                                   + sock.getsockname()[1])

    def _acceptSocket(self, datasock: socket, handler: Callable,
                     show_info: bool = False):
        """Awaits sockets connecting to serverdatasocks.

        ...

        Similar to `_acceptClient()` but instead of accepting new
        clients, this function accepts connections to a *serverdatasock*
        for established client connections. This function gets called
        with `newDataSock()`.

        ---
        Parameters
        ----------
        datasock : socket
            Datasock that accepts new sockets
        handler : Callable
            Function that handles receiving and interpreting data
        show_info : bool, optional
            Output status and connect information

        ---
        See Also
        --------
        newDataSock : Creates a datasock and accepts new sockets
        _registrateSocket : Assigns a socket to the corresponding client
        _acceptClient : Accepts new clients connecting to the serversock

        ---
        Examples
        --------
        >>> s.newDataSock('Datasock_1', recvClientData)
        <socket ...>
        """

        while self.se_running:
            sock, (ip, port) = None, ('', -1)
            try:
                try:
                    sock, (ip, port) = datasock.accept()
                except OSError:  # The server gets shut down
                    return
                if self.se_running:
                    Thread(
                        target=self._registrateSocket,
                        args=(sock, datasock, handler, show_info),
                        name=f"Recv_{datasock.getsockname()[1]}"
                             + f"{ip.split('.')[-1]}"
                    ).start()
            except (OSError, IndexError):  # Client closed socket
                if self.se_running and show_info:
                    self.logEvent(
                        f"Lost connection with unidentified new datasock({ip})"
                        + f"on the Server-socket {datasock.getsockname()[1]}")

    def _registrateClient(self, client: socket):
        """Checks compatibility and exchanges metadata with new clients.

        ...

        Sockets that connect to the *serversock* get checked if they can
        communicate with it. If so server and client exchange metadata
        and a username for the client gets set. After that *datasocks*
        get connected (if the server has any) and `recvUserMessages()`
        receives and evaluates data for that client socket.

        ---
        Parameters
        ----------
        client : socket
            Socket that needs to be registered

        ---
        See Also
        --------
        _acceptClient : Accepts new clients on the serversock
        _registrateSocket : Registers sockets on serverdatasocks

        ---
        Notes
        -----
        - Only client sockets are allowed to connect to the serversock.
        If a client datasocket connects to the serversock, or a client
        connects to a server datasock the socket gets disconnected.
        """

        connid = self._generateNewConnID()
        clientaddr = client.getpeername()
        conntype = ''
        try:
            # Validate sockettype
            try:
                client.settimeout(0.1)
                if client.recv(32).decode() == 'clientsocket':
                    client.send('suited sockettype'.encode())
                else:
                    client.send('unsuited sockettype'.encode())
                    raise TimeoutError
                client.settimeout(None)
            except TimeoutError:
                client.close()
                self.connectionInfo(
                    f"{clientaddr[0]} is unsuited for the server")
                return

            # Check connection type and version
            conntype, version = client.recv(64).decode().split('|', 1)
            version = version.split('.')
            if conntype == 'SERVERFINDER':
                self.logEvent(
                    f"{clientaddr[0]} searches server and disconnected")
                raise ConnectionResetError
            elif (conntype == 'CLIENT' or conntype == 'SUBSERVER') \
                    and int(version[0]) < 6 and int(version[1]) < 26:
                self.logEvent(clientaddr[0] + " is not compatible")
                raise ConnectionAbortedError

            # Exchange serverdata
            binary_serverdata = dumps(self.getServerData())
            if len(binary_serverdata) > 4096:
                self.errorInfo("Serverdata is larger than 4096 bytes and "
                               + f"registering {clientaddr[0]} will fail.")
                raise ConnectionAbortedError
            client.send(binary_serverdata)

            # Exchange clientdata
            clientdata = (loads(client.recv(4096)))
            username = clientdata['username']
            del clientdata['username']

            # Validate username
            username_changed_info = ""
            if username == '' \
            or not 3 <= len(username) <= self._max_username_length \
            or username.lower() in self._restricted_usernames \
            or self.getIDof(username=username) is not None:
                if username == '': pass
                elif not self._min_username_length <= len(username) <= \
                self._max_username_length \
                or username.lower() in self._restricted_usernames:
                    username_changed_info = f"Username '{username}' is invalid"
                if self.getIDof(username=username) is not None:
                    username_changed_info = \
                                f"Username '{username}' is already used"
                username = f'unnamed_{str(connid)[:5]}'
            client.send(username.encode())

            # Await client processing registration
            if not client.recv(32).decode() == 'continue':
                raise ConnectionResetError

        except (ConnectionResetError, ConnectionAbortedError, EOFError):
            if conntype != 'SERVERFINDER':
                self.connectionInfo(clientaddr[0]
                                    + " disconnected during registration")
            client.close()
            return

        # PASSED REGISTRATION

        conn_entry = {
            'name': username,
            'socks': {self.addr[1]: client},
            'isserver': conntype == 'SUBSERVER',  # Client is network node
            'addr': clientaddr,
            'clientdata': clientdata,  # Metadata sent from the client
            'permissions': ['user'],
            'muted': False,
            'connecttime': time(),
            'ping': -0.001,
            'data': {  # Array holds data for different use cases
                'recv_buffer': {},  # Buffers received data per socket
                'recv_packets': {}  # Holds incomplete data per socket
            }}
        self.conns[connid] = conn_entry

        # Connect serverdatasockets
        for sockname, sockdata in self.serversocks.items():
            if sockdata[1] and sockname != 'Serversock':
                self.sendCommandTo(
                    conn_entry['socks'][self.addr[1]],
                    'newdatasock',
                    [sockdata[0].getsockname()])

        # Ping socket
        if 'Maindata' in self.serversocks:
            started = time()
            while self.getMainDataPort() not in conn_entry['socks']:
                sleep(0.001)
                if time() > started + 1.0:
                    break
            else:
                self.conns[connid]['ping'] = self.pingSocket(
                    self.mainDataSockof(connid))
        else:
            started = time()
            self.sendDataTo(client, ['<$REQUEST$>', 'request', '0', 'PING'])
            client.recv(128)
            self.conns[connid]['ping'] = time() - started

        # Welcome text
        if username_changed_info != "":
            self.sendMsgTo(connid, username_changed_info)
        self.connectionInfo(f"{clientaddr[0]} is registered as '{username}'")
        self.sendMsgTo(connid, f"Connected to {self.username}")
        self.sendMsgTo(connid, f"Registered as '{username}'")
        self.sendMsgTo(connid, "Type 's.help()' for more information")
        if self.adminkey == '':
            conn_entry['permissions'].append('admin')
            self.sendMsgTo(connid, "You have admin permissions")

        self.recvUserMessages(connid, client)

    def _registrateSocket(self, datasocket: socket,
                         serversock: socket,
                         handler: Callable, show_info: bool=False):
        """Registers a socket on a datasock and links it to a client.

        ...

        Client sockets connecting to *datasocks* get picked up by the
        `_acceptSocket()` function for the corresponding sock which calls
        this function which checks if server and client socket are
        compatible. If the socket is compatible, it sends the address of
        the client through which the socket can be linked to its client.

        ---
        Parameters
        ----------
        datasocket : socket
            Socket that needs to be registered
        serversock : socket
            Serversock that made the connection with the datasocket
        handler : Callable
            Function that interacts with the socket once registered
        show_info : bool, optional

        ---
        See Also
        --------
        registerClient : Registers a new connected client
        _acceptSocket : Accepts new sockets on server datasocks

        ---
        Notes
        -----
        - This is used for every datasock no matter what **handler**
        function is chosen.
        """

        try:
            # Validate sockettype
            datasocket.settimeout(0.1)
            if datasocket.recv(32).decode() != 'datasocket':
                datasocket.send('unsuited sockettype'.encode())
                raise TimeoutError
            else:
                datasocket.send('suited sockettype'.encode())
            datasocket.settimeout(None)
        except (TimeoutError, UnicodeDecodeError):
            if show_info:
                self.connectionInfo(
                    datasocket.getsockname()[0]
                    + " is unsuited for sock '"
                    + self.getSockData(port=serversock.getsockname()[1])[3]
                    + "'")
            datasocket.close()
            return

        # Identify what user the socket belongs to
        port = -1  # Should not be displayed
        try:
            port = datasocket.getsockname()[1]
            recv = datasocket.recv(self.se_max_datasize)
            useraddr = loads(recv)
            userid = self.getIDof(addr=useraddr)
            self.conns[userid]['socks'][port] = datasocket
            if show_info:
                self.logEvent("User '" + self.conns[userid]['name']
                              + "' connected a new datasocket at port "
                              + str(serversock.getsockname()[1]))
            Thread(
                target=handler,
                args=(datasocket, userid,),
                name='Recv_{}_{}'.format(
                    serversock.getsockname()[1],
                    datasocket.getsockname()[0].split('.')[-1])
            ).start()
        except (ConnectionResetError, ConnectionAbortedError, OSError):
            self.logEvent("An unassociated socket on datasock"
                + f"'{self.getSockData(port=port)[3]}' ({port}) disconnected")

    def disconnectConn(self, clientid: str):
        """Disconnects a client from the server.

        ...

        This disconnects a client and its connections to other datasocks
        from the server.

        ---
        Parameters
        ----------
        clientid : str
            ID of a client
        """

        # Client side close
        self.sendCommandTo(self.mainSocketof(clientid), 'disconnect')

        # server side close (if the client does not disconnect)
        try:
            port = self.addr[1]
            self.getSocketof(clientid, port).close()
        except ValueError:
            pass

    def recvFuncWrapper(recvFunc: Callable):  # type: ignore
        """Decorator/Wrapper for receiving Functions (recvFuncs).

        ...

        **This function should be used as a decorator for every
        receiving function *(recvFunc)* **.

        Loops the **recvFunc** as long as data can/should be received.
        Also manages exceptions and proper disconnects and socket
        removal if the connection got terminated. The wrapped function
        must receive data with `socket.recv()`. The primary recvFunc
        is `recvClientData()`.

        The wrapper adds an entry to the *recv_buffer* and *recv_packet*
        dicts in `Server.conns[*clientid*]['data']`. The entries can be
        addressed with the port of the client socket. This is used to
        pass incomplete data to the next call of **recvFunc** to be
        completed.

        ---
        Parameters
        ----------
        recvFunc : Callable
            Wrapped function that receives and evaluates data

        ---
        Wrapped function parameters
        ---------------------------
        datasocket : socket
            Socket from which data is received and evaluated
        clientid : str
            ID of the client corresponding to the socket
        *args : list
            Unspecified arguments
        **kwargs : list
            Unspecified keyword arguments

        ---
        Notes
        -----
        - A **recvFunc** also needs a suited send function.
        - The wrapped function will always be passed a **datasocket**
        and **clientid**.

        ---
        Examples
        --------
        >>> @recvFuncWrapper
        ... def recv(datasocket, clientid):
        ...     data = datasocket.recv(s.max_datasize)
        ...     print(data.decode())

        >>> @recvFuncWrapper
        ... def recv2(datasocket, clientid, bytes, buffer=None):
        ...     buffer += datasocket.recv(bytes).decode()
        ...     # Process data
        ...     return buffer
        """

        def inner(self, datasocket: socket, clientid: str, *args,
                  **kwargs):
            port = datasocket.getsockname()[1]
            self.conns[clientid]['data']['recv_buffer'][port] = b''
            self.conns[clientid]['data']['recv_packets'][port] = {}

            try:
                while self.se_running:
                    recvFunc(self, datasocket, clientid, *args, **kwargs)
                raise ConnectionResetError
            except (ConnectionResetError, ConnectionAbortedError, OSError):
                self.logEvent(
                    f"Terminated socket ({port}) for user '"
                    + self.conns[clientid]['name'] + "'")
                datasocket.close()
                del self.conns[clientid]['data']['recv_buffer'][port]
                del self.conns[clientid]['data']['recv_packets'][port]
            if clientid in self.conns:
                del self.conns[clientid]['socks'][port]
        return inner

    @recvFuncWrapper
    def recvAndOutput(self, datasocket: socket, clientid: str,
                      bytes: int):
        """Simple receive Function that outputs the received data.

        ...

        A a very simple receiving Function (recvFunc) showing the
        *socket* principles of receiving data but with handling of
        disconnect and connection errors.

        *This is not further used*

        ---
        Parameters
        ----------
        datasocket : socket
            Socket that receives data from a client socket
        clientid : str
            Identification key of the client with the **datasocket**
        bytes : int
            Receive number of bytes

        ---
        See Also
        --------
        recvClientData : Default recvFunc for commands and python obj
        recvFuncWrapper : Handles connectivity of the socket

        ---
        Notes
        -----
        - This will not work with the `Client.sendData()` function or
        any function build upon since they do not send encoded utf-8
        bytes. Use `socket.send(data.encode())` instead.
        """

        data = datasocket.recv(bytes)
        self.printInfo(data.decode())

    @recvFuncWrapper
    def recvClientData(self, datasocket: socket, clientid: str):
        """Receives and evaluates bytes from a client socket.

        ...

        Receives a byte *packet* from the **datasocket**. The packet
        contains data and metadata informing about the data. If the
        transmitted data is to large for one packet it gets split into
        multiple. Data can be recombined through the information in
        the packet header. Recombined data gets evaluated for
        servercommands and requests. If it is simple text it gets
        displayed.

        ---
        Parameters
        ----------
        datasocket : socket
            Socket that receives data from a client socket
        clientid : str
            Identification key of the client with the **datasocket**

        ---
        See Also
        --------
        recvUserMessages : Receives (mostly text) for the serversock
        newDataSock : Datasock passes a socket to a *recvFunc* function

        ---
        Notes
        -----
        - This is the default function to receive data *(recvFunc)*.
        - The suited send Function is `Client.sendData()`
        - A packet ends with the separator *_se_sep*
        - Received text messages will be *ANSI* formatted (if *ANSI* is
        enabled).

        ---
        Examples
        --------
        >>> s.newDataSock('Datasock_1', recvFunc=s.recvClientData)
        """

        connected_port = datasocket.getsockname()[1]
        buffer = self.conns[clientid]['data']['recv_buffer'][connected_port]
        if len(self.conns[clientid]['data']['recv_packets']) > 16:
            self.warningInfo(
                f"Sock '{self.getSockData(port=connected_port)[3]}' "
                + "has many uncompleted transmission packets")
        buffer += datasocket.recv(self.se_max_datasize)

        # User is muted, no server side action
        if self.conns[clientid]['muted']:
            return

        # Process every packet in received bytes
        while self._se_sep.encode() in buffer:
            packet, buffer = buffer.split(self._se_sep.encode(), 1)
            try:
                packet = loads(packet)
            except UnpicklingError:
                self.warningInfo(
                    f"A received packet from '{self.conns[clientid]['name']}' "
                    + f"on sock '{self.getSockData(port=connected_port)[3]}' "
                    + "cannot be decoded")
                continue

            # Combine multiple packages to get larger data
            if packet[2] > 0:
                if packet[0] not in self.conns[clientid]['data'][
                'recv_packets']:
                    self.conns[clientid]['data']['recv_packets'][packet[0]] = \
                        packet[3]
                    continue
                self.conns[clientid]['data']['recv_packets'][packet[0]] += \
                    packet[3]
                if packet[1] != packet[2]:
                    continue
                packet[3] = self.conns[clientid]['data']['recv_packets'][
                    packet[0]]
                del self.conns[clientid]['data']['recv_packets'][packet[0]]

            # Evaluate received data
            packet[3] = packet[3].replace(
                eval("'<$-' + '$SEP$' + '-$>'").encode(),
                self._se_sep.encode())
            try:
                data = loads(packet[3])
            except UnpicklingError:
                self.warningInfo(
                    f"Received data from '{self.conns[clientid]['name']}' on "
                    + f"sock '{self.getSockData(port=connected_port)[3]}' is "
                    + "unreadable and will be ignored")
                continue

            # Display onto server console if a text
            if isinstance(data, str):
                # Format servercommand
                if len(data) > 0 and data[-1] == ')' and '(' in data \
                and data.startswith('s.'):
                    command, command_args = data[:-1].replace(' ', '').split(
                        '(', 1)
                    command_args = command_args.split(',')
                    message = (f"\033[0;1;4m{command}\033[0m(\033[3m"
                            + "\033[0m, \033[3m".join(command_args)
                            + "\033[0m)")
                # Format normal text
                else:
                    message = data + '\033[0m'
                    self.sendMsgTo(clientid, "\033[3mReceived:\033[0m " + data)
                self.printInfo(
                    message,
                    sender=f"\033[0;1m[\033[4;53m"
                        + f"{datetime.now().strftime('%H:%M:%S')}\033[0m]"
                        + f"\033[3m{self.conns[clientid]['name']}\033[0m: ")

            # Process a request
            if isinstance(data, list) and data[0] == '<$REQUEST$>':
                if data[1] == 'request':  # Client is requesting
                    try:
                        value = self.se_requestables.get(data[3])
                        if callable(value):
                            value = value()
                        self.sendDataTo(
                            datasocket,
                            ['<$REQUEST$>', 'answer', data[2], value])
                    except AttributeError:
                        self.sendDataTo(
                            datasocket,
                            ['<$REQUEST$>', 'answer', data[2],
                             f"No requestable '{data[3]}'"])
                elif data[1] == 'answer':  # Client sent an answer
                    if data[2] in self._open_requests:
                        self._open_requests[data[2]] = data[3]
                    else:
                        self.warningInfo(
                            "Received requested data after timeout")
                else:
                    self.errorInfo(f"Invalid request phrase '{data[1]}'")

            # Process a servercommand
            elif isinstance(data, str) and len(data) > 0 \
            and data[-1] == ')' and '(' in data \
            and data[1] == '.':
                function, args = data.replace(', ', ',').replace(' ,', ',') \
                    [:-1].split('(', 1)
                args = args.split(',')
                if args == ['']:
                    args = []
                self.execServercommand(clientid, function, args)

            # Data(type/-format) can't be processed
            elif not isinstance(data, str):
                    self.warningInfo(
                        "Could not identify the purpose of a "
                        + f"{type(data)} obj sent by user '"
                        + self.conns[clientid]['name'] + "'")
        self.conns[clientid]['data']['recv_buffer'][connected_port] = buffer

    def recvUserMessages(self, clientid: str, sock: socket):
        """Receives messages (and data) for a client on the serversock.

        ...

        ---
        Parameters
        ----------
        clientid : str
            ID of the client whose messages get received
        sock : socket
            Socket on the serversock that receives the messages

        ---
        See Also
        --------
        recvClientData : Receives and evaluates data for a sock

        ---
        Notes
        -----
        - This is the default recvFunc of the serversock
        - This calls the standard receiving function `recvClientData()`
        (which is wrapped by `recvFuncWrapper`).
        - If the connection to the serversock is lost, the client with
        all sockets get disconnected.
        """

        self.recvClientData(sock, clientid)
        # Remove whole client if serversock connection fails
        started = time()
        while len(self.conns[clientid]['socks']) > 0:
            sleep(0.001)
            if time() - started > 0.5:
                self.errorInfo("Unable remove datasockets for '"
                               + self.conns[clientid]['name'] + "'")
                break
        self.connectionInfo("Disconnected connection '"
                            + self.conns[clientid]['name'] + "'")
        del self.conns[clientid]

    def sendDataTo(self, clientsocket: socket | str, data: Any):
        """Sends data through a server sock to the client.

        ...

        Binary encodes the data object and splits it into multiple
        *packets* if it exceeds the *max_datasize* for one transmission.
        *Packets* header informing about number of packets and id of
        the data transmission. The *packets* get sent one by one to the
        client socket.

        ***Not to be confused with `network.Client.sendData()`!***

        ---
        Parameters
        ----------
        clientsocket : socket | str
            ClientID or a socket that transmits the data
        data : object
            Picklable python object that gets transmitted

        ---
        See Also
        --------
        sendMsgTo : Sends a message to a client
        sendCommandTo : sends a *clientcommand* call
        sendRequestTo : Requests data from a client

        ---
        Notes
        -----
        - The ID of a client can be gained with `getIDof()`.
        - A separator informs about the end of a *packet*.
        - Unpicklable data can only be transmitted through a custom
        *datasock* and *handler* function. See `newDatasock()` and
        `recvClientData()` for reference.

        ---
        Examples
        --------
        >>> s.sendDataTo(getIDof('client'), "Hello World!")

        >>> s.sendDataTo(getIDof('client'), [1, 2, 3.3, 42.0])

        >>> socket = s.conns[getIDof('client')]['socks'][addr[1]]
        >>> s.sendDataTo(socket, {'key1': True, 'key2': 6.9})
        """

        transmission_id = self._generateTransmissionID()
        try:
            data = dumps(data)
        except PicklingError:
            self.errorInfo("Transmitting data cannot be converted to bytes")
            return
        # Data can't contain the original separator to be usable
        data = data.replace(self._se_sep.encode(),
                            eval("'<$-' + '$SEP$' + '-$>'").encode())

        # Calculate bytes of packet header (100 bytes to be safe)
        header_size = len(dumps([
            transmission_id, 0, int(len(data)/self.se_max_datasize),
            b'']) + self._se_sep.encode()) + 10
        data_per_packet = (self.se_max_datasize-header_size)
        needed_packets = int(len(data)/data_per_packet) + 1

        # Send packets
        if isinstance(clientsocket, str):
            clientsocket = self.mainSocketof(clientsocket)
        try:
            for pack in range(needed_packets):
                clientsocket.send(
                    dumps([
                        transmission_id, pack, needed_packets - 1,
                        data[pack*data_per_packet:(pack+1)*data_per_packet]])
                    + self._se_sep.encode())
        except ConnectionAbortedError:
            pass
        except Exception as e:
            clientid = self.getIDof(socket=clientsocket)
            if clientid in self.conns:
                self.errorInfo("Senderror while sending to '"
                               + self.conns[clientid]['name'] + "':  "
                               + str(e))
            else:
                self.warningInfo("Senderror for a disconnected client")
            self.logEvent(f"Occurred error: {e}")

    def sendMsgTo(self, clientid: str, message: str):
        """Sends a message to a client through the serversock.

        ...

        ***Not to be confused with `network.Client.sendMsg()`!***

        ---
        Parameters
        ----------
        clientid : str
            ID of a client
        message : str
            Information that gets transmitted

        ---
        See Also
        --------
        sendDataTo : Sends data to a client
        sendCommandTo : sends a *clientcommand*
        sendRequestTo : Requests data from a client

        ---
        Examples
        --------
        >>> s.sendMsgTo(getIDof('client'), "Hello")
        """

        if not message:
            return
        self.sendDataTo(self.mainSocketof(clientid), message)

    def sendCommandTo(self, clientsocket: socket | str, command: str,
                      arguments: Iterable[Any] = None):  # type: ignore
        """Sends a (client)command to a client.

        ...

        Transmits a list containing a clientcommand indicator, the
        command name and its arguments. The client then executes the
        command if it is valid.

        ---
        Parameters
        ----------
        clientsocket : socket | str
            ClientID or a socket that transmits the command
        command : str
            Name of the command
        arguments : Iterable[Any], optional
            Arguments needed to execute the command

        ---
        See Also
        --------
        sendDataTo : Sends data to a client
        sendMsgTo: Sends a message(str) to a client
        sendRequestTo : Requests data from a client

        ---
        Notes
        -----
        - If the clientID is used for **clientsocket**, the command
        gets sent through the serversock connection.
        - Available *clientcommands* are set by the client and can be
        viewed in the **clientdata** entry of the **conns** dict.

        ---
        Examples
        --------
        >>> socket = s.conns[getIDof('client')]['socks'][addr[1]]
        >>> s.sendCommandTo(socket, 'disconnect')
        >>> s.sendCommandTo(socket, 'connect', ['192.168.178.140', 4000])
        >>> s.sendCommandTo(socket, 'newdatasock',
        ...    [serversocks, sockdata[0].getsockname()])
        """

        if arguments is None:
            arguments = []
        else:
            try:
                if isinstance(arguments, str):
                    raise TypeError
                arguments = list(arguments)
            except TypeError:
                arguments = [arguments]

        self.sendDataTo(clientsocket, ['<$COMMAND$>', command, arguments])

    def sendRequestTo(self, clientsocket: socket | str,
                      requested: str, timeout: float | None = 1.0,
                      get_time: bool = False
                      ) -> Any | tuple[Any, float]:
        """Requests data from a client and returns it.

        ...

        Sends a *request* containing a request indictor, an request
        identification key and the **requested** *requestable*. If a
        client has such a *requestable*, it  will send the data together
        with the request identification key and an 'request answer'
        indicator back. The *receiving* thread for a server stored the
        data in an array in the conns[_]['data'] dict, where it gets
        collected and returned.

        ***Not to be confused with `network.Client.sendRequest()`!***

        ---
        Parameters
        ----------
        clientsocket : socket | str
            Clientid or socket that sends the request
        requested : str
            Name of a client requestable
        timeout : float | None, optional
            Timeout the request after n seconds
        get_time : bool, optional
            Additionally return the time needed to get the data

        ---
        Returns
        -------
        object : Data of the client *requestable*
        None : If the timeout is reached or no **requested** available
        tuple[object, float] : The requested data and execution time

        ---
        Notes
        -----
        - If the clientid is used for **clientsocket**, the request is
        made through the serversock.
        - Available *requestables* are set by the client.
        - *Requestables* should be in uppercase.
        - The syntax of a sended request is similar to a sended
        *clientcommand* call.

        ---
        Examples
        --------
        >>> socket = s.conns[getIDof('client')]['socks'][addr[1]]
        >>> s.sendRequestTo(socket, 'CLIENTDATA')
        {...}
        >>> s.sendRequestTo(socket, 'CLIENTDATA', 2.0, get_time=True)
        [{...}, 0.05]
        >>> s.sendRequestTo(socket, 'UNDEFINED_REQUEST_NAME')
        None
        """

        if len(self._open_requests) > 50:
            self.warningInfo(f"Many{len(self._open_requests)} open requests")
        try:
            if isinstance(clientsocket, str):
                id = clientsocket
                clientsocket = self.mainSocketof(clientsocket)
            else:
                id = self.getIDof(socket=clientsocket)
            if self.conns[id]['muted']:
                self.warningInfo("The user '" + self.conns[id]['name']
                                 + "' is muted and requests can't be answered")

            # Send request
            key = self._generateRequestID()
            self._open_requests[key] = requested
            starttime = time()
            self.sendDataTo(clientsocket,
                            ['<$REQUEST$>', 'request', key, requested])

            # Await response
            while self.se_running and self._open_requests[key] == requested:
                if timeout is not None \
                and time() - starttime >= timeout:
                    if self.getIDof(socket=clientsocket) is not None:
                        self.warningInfo(
                            f"Request for '{requested}' did not receive data")
                    if get_time:
                        return None, time() - starttime
                    else:
                        return None
            starttime = time() - starttime  # Repurposed to runtime
            data = self._open_requests[key]
            del self._open_requests[key]
            if get_time:
                return data, starttime
            else:
                return data
        except KeyError:
            return None

    def changeConnName(self, clientid: str, newname: str):
        """Changes the username for a client and syncs the changes.

        ...

        Checks if the **newname** is a valid username. If the name is
        valid it gets changed server side and client side. The user will
        be informed about the name change.

        ---
        Parameters
        ----------
        newname : str
            New username of the connection
        clientid : str, optional
            ID of a connection

        ---
        Raises
        ------
        ValueError: **newname** is already used by another client
        ValueError: **newname** is a restricted name and can't be used
        ValueError: **newname** is to short or to long

        ---
        Notes
        -----
        - The new username must have a certain length in the range of
        the attributes `_min_username_length` and `max_username_length`.
        - The new username may not be a restricted username (attribute
        `_restricted_usernames`) and may not be used by another client
        already.
        """

        if not self._min_username_length <= len(newname) <= \
        self._max_username_length:
            raise ValueError("The new username needs to be in between 3 and "
                + f"{self._max_username_length} characters")
        elif self.getIDof(username=newname) is not None:
            raise ValueError(f"The username '{newname}' is already used")
        elif newname.lower() in self._restricted_usernames:
            raise ValueError(f"The username '{newname}' is a restricted name")

        self.connectionInfo(f"User '{self.conns[clientid]['name']}' changed "
                            + f"name to '{newname}'")
        self.conns[clientid]['name'] = newname
        self.sendCommandTo(self.mainDataSockof(clientid), 'changename',
                           [newname])
        self.sendMsgTo(
            clientid, f"Your username changed to '\033[1m{newname}\033[0m'")

    # --------------------------------+
    # Servercommand and -requestables |
    # --------------------------------+

    def newServerCommand(self, name: str, description: str, action: Callable,
                         call_as_thread: bool = False,
                         needed_permission: list[str] | str = 'user',
                         args: list[str] | str = [],
                         optional_args: list[str] | str = [],
                         repeatable_arg: str = None,  # type: ignore
                         category: str = '',
                         overwrite: bool = False):
        """Creates a new servercommand.

        ...

        Servercommands are short scripts that can be called by a client
        and get executed on the server machine. A servercommand can
        have required and optional parameters as well as a repeatable
        parameter. Clients need certain permissions to call a
        servercommand.

        ---
        Parameters
        ----------
        name : str
            Name of the command starting with 's.'
        description : str
            Short description of the command
        action : Callable
            Script that gets executed when the command is called
        call_as_thread : bool
            Execute the action in a new thread
        needed_permission : list[str] | str, optional
            Permissions required to run this command
        args : list[str] | str, optional
            Names of required arguments
        optional_args : list[str] | str, optional
            Names of optional arguments
        repeatable_arg : str, optional
            Name of a repeatable argument
        category : str, optional
            Category this command is enlisted in
        overwrite : bool, optional
            Overwrite an existing command

        ---
        Raises
        ------
        NameError: Command needs to start with 's.'

        ---
        See Also
        --------
        delServercommand : Deletes a servercommand
        _initServercommands : Initializes available servercommands

        ---
        Notes
        -----
        - Not calling long commands in a new thread decreases the
        responsiveness of that client.
        - If an argument is repeatable and optional, it must be stated
        in both parameters of the method.
        - The arguments **args**, **optional_args**,
        **repeatable_arg** and **description** are only informational.
        - The **category** lists commands in a specific order when
        displayed with 's.help(commands)' but is otherwise also only
        informational.
        - The **action** gets called with two arguments: the *clientid*
        and a list with passed *arguments*.

        ---
        Examples
        --------
        >>> s.newServerCommand('s.greet', "Greet a person",
        ...     lambda id, args: print(f"Hello {args[0]}!"),
        ...     args='name')

        >>> s.newServerCommand('s.restart', "Restarts the Server",
        ...     lambda id, args: restartServer(),
        ...     call_as_thread=True,
        ...     needed_permission='admin',
        ...     category='server management')

        >>> s.self.newServerCommand('s.removeadmin', "...",
        ...     lambda id, args: ...,
        ...     optional_args=['username'],
        ...     repeatable_arg='username',
        ...     needed_permission=['admin', 'owner'])
        >>> s._getFormattedCommandParams('s.removeadmin')
        (username[o][r])
        """

        if isinstance(needed_permission, str):
            needed_permission = [needed_permission]
        if isinstance(args, str):
            args = [args]
        if isinstance(optional_args, str):
            optional_args = [optional_args]

        if '' in args + optional_args + [repeatable_arg]:
            self.warningInfo(
                f"Defining servercommand '{name}' with an empty str argument")

        if name in self.se_commands and not overwrite:
            self.warningInfo(f"Servercommand '{name}' already exists and needs"
                           + " to be overwritten to change it")
        elif not name.startswith('s.'):
            raise NameError(f"Servercommand '{name}' needs to start with"
                           + " 's.' to be callable")
        elif not (isinstance(repeatable_arg, type(None)) or optional_args == []
        ) and not repeatable_arg == optional_args[-1]:
            self.errorInfo(
                f"Repeatable argument '{repeatable_arg}' must be last "
                + "optional argument (for servercommand '{name}')")
        else:
            if name not in self.se_commands and overwrite:
                self.warningInfo(
                    f"Creating new servercommand since no '{name}' exists")
            self.se_commands[name] = (
                action, call_as_thread, needed_permission,
                args, optional_args, repeatable_arg,
                description, category)

    def delServerCommand(self, name: str):
        """Deletes a Servercommand.

        ...

        Parameters
        ----------
        name : str
            Name of the command

        ---
        Raises
        ------
        NameError : No such servercommand exists

        ---
        See Also
        --------
        newServerCommand : Creates a new Servercommand
        """

        if name in self.se_commands:
            del self.se_commands[name]
        else:
            raise NameError(f"No servercommand named '{name}'")

    def newServerRequestable(self, name: str, data: object,
                             overwrite: bool = False):
        """Creates a requestable allowing the client to request data.

        ...

        Parameters
        ----------
        name : str
            Name of the requestable
        data : object
           Value (or getter function) that gets sent to the client
        overwrite : bool, optional

        ---
        Raises
        ------
        KeyError : No such requestable

        ---
        See Also
        --------
        _initServerRequestables : Initiates available requestables
        delServerRequestable : Deletes a requestable

        ---
        Notes
        -----
        - **data** can be a value or a function with a return value. If
        it is a function it will be executed and its returned value sent
        to the client.
        - Requestables should be written in uppercase but this is not
        enforced.

        ---
        Examples
        --------
        >>> s.newServerRequestable('PI', 3.1415)

        >>> s.newServerRequestable('NUM_SOCKS', lambda: len(serversocks))

        >>> from time import time
        >>> s.newServerRequestable('TIME', time())  # Fixed time
        >>> s.newServerRequestable('TIME', time, True)  # Current time
        """

        if name in self.se_requestables and not overwrite:
            self.warningInfo(f"Requestable '{name}' already exists and needs"
                             + " to be overwritten to change it")
            return
        if name not in self.se_requestables and overwrite:
            self.warningInfo("Creating new requestable since no key "
                             + f"'{name}' exists")
        self.se_requestables[name] = data

    def delServerRequestable(self, name: str):
        """Deletes a serverrequestable.

        ...

        Parameters
        ----------
        name : str
            Name of the requestable

        ---
        Raises
        ------
        NameError : Requestable does not exist

        ---
        See Also
        --------
        newServerRequestable : Create a new Requestable

        Notes
        -----
        - Requestables allow client to request certain data from the
        server.

        ---
        Examples
        --------
        >>> s.newServerRequestable('PI', 3.1415)
        >>> s.delServerRequestable('PI')
        """

        if name in self.se_requestables:
            del self.se_requestables[name]
        else:
            raise NameError(f"No server requestable named '{name}'")

    def _initServercommands(self):
        """Defines servercommands that are available for clients.

        ...

        Initiated servercommands:
        *([o]: optional arguments, [r]: repeatable argument)*
        - s.closedatasock(serversockname[r])
        - s.restart()
        - s.services(enable, service_name[o])
        - s.services_info()
        - s.setadminkey(new_key)
        - s.shutdown()
        - s.storelog(filename[o])
        - s.attributes()
        - s.errortrace()
        - s.getadminkey()
        - s.help(servercommand[o][r])
        - s.info(entity[o][r])
        - s.listsocks()
        - s.listthreads()
        - s.changename(newname, clientname[o])
        - s.connectto(ip, port[o])
        - s.getadmin(adminkey[o])
        - s.getrights(permission[r])
        - s.kickip(ip[r])
        - s.kickuser(username[r])
        - s.mute(username[r])
        - s.ping()
        - s.removeadmin(username[o][r])
        - s.removerights(permission[r])
        - s.unmute(username[r])

        ---
        See Also
        --------
        newServerCommand : creates a new Servercommand

        ---
        Notes
        -----
        - Sending 's.help(commands)' from a client will list available
        servercommands.
        - The *s.help()* command can be used to show informational texts
        regarding the project, usage of the program or for information
        about available servercommands and how to use them.
        - The *s.info()* command can be used to get the state of the
        server, clients or users. It can also be used to get available
        servercommands.
        """

        def program_help(clientid, args):
            # General help
            if len(args) == 0:
                self.sendMsgTo(
                    clientid,
                    "\033[1;4mSERVER HELP\033[0;1m:\033[0m\n"
                    + "  If you don't know how to interact/operate this\n"
                    + "  server then please refer to the usage examples on\n"
                    + "  https://github.com/OmegaDawn/localthingsnet \n\n"
                    + "  Information about the server and the underlying\n"
                    + "  project can be gained by sending "
                    +"'\033[1ms.help(server)\033[0m'\n"
                    + "  and '\033[1ms.help(project)\033[0m'. For available\n"
                    + "  servercommands type '\033[1ms.help(commands)\033[0m'."
                )

            # Project information
            elif args[0] == 'project':
                self.sendMsgTo(
                    clientid,
                    "\033[1;4mLOCALTHINGSNETWORK PROJECT\033[0;1m:\033[0m\n"
                    + "  This is an application of the localthingsnet(work)\n"
                    +"  project(https://github.com/OmegaDawn/localthingsnet)\n"
                    + "  The project aims to provide a socket based\n"
                    + "  communication tool for personal DIY and/or IoT\n"
                    + "  projects that need a simple and easy to setup\n"
                    + "  connection to other devices. Further information can\n"
                    + "  be found in the already mentioned repository.")

            # Server information
            elif args[0] == 'server':
                self.sendMsgTo(
                    clientid,
                    "\033[1;4mSERVER DESCRIPTION\033[0;1m:\033[0m\n"
                    + f"  (Name: {self.username}, Type: {type(self).__name__})"
                    + f"\n    {self.description}")

            # Overall servercommand help
            elif args[0].lower() in ['command', 'commands', 'servercommands']:
                sendtext = (
                    "\033[1;4mAVAILABLE SERVERCOMMANDS\033[0;1m:\033[0m"
                    + '\n  Use "s.help(*command_name*)" for more'
                    + "\n    information about that command"
                    + "\n  Parameters with a '[o]' are optional"
                    + "\n  Parameters with a '[r]' are repeatable\n")

                # Group commands by their category
                groups = {}
                for name in sorted(self.se_commands):
                    if self.se_commands[name][7] not in groups:
                        groups[self.se_commands[name][7]] = [name]
                    else:
                        groups[self.se_commands[name][7]].append(name)

                # Format commands
                for group in sorted(groups):
                    if group != '':
                        sendtext += f"\n  {group} commands:"
                    for name in groups[group]:
                        if group != '':
                            sendtext += f"\n    {name}"
                        else:
                            sendtext += f"\n  {name}"
                        sendtext += self._getFormattedCommandParams(name)
                self.sendMsgTo(clientid, sendtext)

            # Not literal *command_name*
            elif args[0] == '*command_name*':
                self.sendMsgTo(
                    clientid,
                    "'\033[1m*command_name*\033[0m' is not meant\n"
                    + "  literally. Type something like to\n"
                    + " 's.help(s.info)' to get information about\n"
                    + "  that command. If you don't know any commands,\n"
                    + "  type 's.help(commands)' to get a list of all\n"
                    + "  available commands and the categories they are\n"
                    + "  enlisted in. Alternatively commands in a\n"
                    + "  certain category can be shown with \n"
                    + "'s.help(*category* commands)'")

             # Category command help
            elif args[0].endswith(' commands'):
                args[0] = args[0].replace(' commands', '')
                category_commands = []
                for command in self.se_commands.items():
                    if command[1][7] == args[0]:
                        category_commands.append(command[0])
                if len(category_commands) > 0:
                    sendtext = f"Available '{args[0]}' commands:"
                    for command in sorted(category_commands):
                        sendtext += f"\n  {command}"
                        sendtext += self._getFormattedCommandParams(command)
                else:
                    sendtext = f"No '{args[0]}' command category"
                self.sendMsgTo(clientid, sendtext)

            # Specific servercommand help
            else:
                infostr = "\033[1;4mSERVERCOMMAND INFO:\033[0m"
                for command in args:
                    command = command.split('(', 1)[0]
                    if not command.startswith('s.'):
                        command = 's.' + command
                    if command not in self.se_commands:
                        infostr += f"\n  No servercommand '{command}'"
                    else:
                        infostr += (
                            f"\n  " + command
                            + self._getFormattedCommandParams(command))
                        infostr += f"\n    {self.se_commands[command][6]}"
                        infostr += (
                            f"\n    Needs '"
                            + ", ".join(self.se_commands[command][2])
                            + "' permissions")
                self.sendMsgTo(clientid, infostr)

        def info(clientid, args):
            # Info of servers
            if len(args) == 0:
                self.sendMsgTo(clientid, self._get_infotext_server(
                    'admin' in self.conns[clientid]['permissions']))
            # Info of entity (user, services, commands)
            else:
                for a in args:
                    if a == 'commands' or a == 'servercommands':
                        program_help(clientid, ['commands'])
                    elif a == 'server':
                        self.sendMsgTo(clientid, self._get_infotext_server(
                            'admin' in self.conns[clientid]['permissions']))
                    elif self.getIDof(username=a) is not None:
                        self.sendMsgTo(
                            clientid,
                            self._get_infotext_user(a))
                    else:
                        self.sendMsgTo(clientid, f"No user '{a}'")

        def ping(clientid):
            new_ping = self.pingSocket(
                self.mainDataSockof(clientid))  # type: ignore
            self.conns[clientid]['ping'] = new_ping
            if new_ping == -0.001:
                self.sendMsgTo(clientid, f"Ping check could not be concluded")
            else:
                self.sendMsgTo(clientid, f"Ping is {int(new_ping*1000)}ms")

        def changename(clientid, args):
            try:
                if len(args) == 1:  # Change own name
                    self.changeConnName(clientid, args[0])
                else:  # Change name of another client
                    if 'admin' in self.conns[clientid]['permissions']:
                        self.changeConnName(self.getIDof(username=args[1]),
                                            args[0])
                    else:
                        self.sendMsgTo(clientid, "Admin permissions needed to"
                                       + " change the name of another client")
            except ValueError as name:
                self.sendMsgTo(clientid, f"No user '{name}' found")

        def getadmin(clientid, args):
            if not args:  # Equal to args == []
                args = ['']
            if 'admin' in self.conns[clientid]['permissions']:
                self.sendMsgTo(clientid, "You already have admin permissions")
            elif args[0] == self.adminkey:
                self.sendMsgTo(clientid,
                               "Key correct. You got admin permissions")
                self.conns[clientid]['permissions'].append('admin')
            else:
                self.sendMsgTo(clientid, "Adminkey incorrect")

        def setadminkey(clientid, args):
            self.adminkey = args[0]
            self.sendMsgTo(clientid, f"Changed adminkey to '{args[0]}'")

        def removeadmin(clientid, args):
            if len(args) == 0:
                if 'admin' in self.conns[clientid]['permissions']:
                    self.conns[clientid]['permissions'].remove('admin')
                self.sendMsgTo(clientid, "Removed admin permissions")
            else:
                for arg in args:
                    removeid = self.getIDof(username=arg)
                    if removeid is not None:
                        if ('admin' in self.conns[removeid]['permissions']):
                            self.conns[removeid]['permissions'].remove('admin')
                            self.sendMsgTo(
                                clientid, "Removed admin permissions of '"
                                + self.conns[removeid]['name'] + "'")
                            if clientid != removeid:
                                self.sendMsgTo(
                                    removeid, "Your admin permissions got "
                                    "removed by '"
                                    + self.conns[clientid]['name']
                                    + "'")
                        else:
                            self.sendMsgTo(
                                clientid,
                                f"user '{arg}' has no admin permissions")
                    else:
                        self.sendMsgTo(clientid, f"No user '{arg}'")

        def mute(clientid, args):
            for arg in args:
                muteid = self.getIDof(username=arg)
                if muteid is not None:
                    if not self.conns[muteid]['muted']:
                        self.conns[muteid]['muted'] = True
                        self.sendMsgTo(
                            muteid, "You got muted by '"
                            + self.conns[clientid]['name'] + "'")
                        self.sendMsgTo(clientid, f"Muted user '{arg}'")
                    else:
                        self.sendMsgTo(clientid,
                                       f"User '{arg}' is already muted")
                else:
                    self.sendMsgTo(clientid, f"No user '{arg}'")

        def unmute(clientid, args):
            for arg in args:
                unmuteid = self.getIDof(username=arg)
                if unmuteid is not None:
                    if self.conns[unmuteid]['muted']:
                        self.conns[unmuteid]['muted'] = False
                        self.sendMsgTo(
                            unmuteid, "You got unmuted by '"
                            + self.conns[clientid]['name'] + "'")
                        self.sendMsgTo(clientid, f"Unmuted user '{arg}'")
                    else:
                        self.sendMsgTo(clientid, f"User '{arg}' is not muted")
                else:
                    self.sendMsgTo(clientid, f"No user '{arg}'")

        def kickuser(clientid, args):
            for arg in args:
                kickuserid = self.getIDof(username=arg)
                if kickuserid is None:
                    self.sendMsgTo(clientid, f"No user '{arg}'")
                    return
                if kickuserid != clientid:
                    self.sendMsgTo(kickuserid, "You got kicked by '"
                                   + self.conns[clientid]['name'] + "'")
                    self.sendMsgTo(clientid, f"Kicked user '{arg}'")
                self.disconnectConn(kickuserid)

        def kickip(clientid, args):
            for arg in args:
                self.statusInfo(f"Disconnecting clients of '{arg}'")
                self.sendMsgTo(clientid, f"Disconnecting clients of '{arg}'")
                for id in self.conns:
                    if self.conns[id]['addr'][0] == arg:
                        name = self.conns[id]['name']
                        if arg != self.conns[clientid]['addr'][0]:
                            self.sendMsgTo(id, "You got kicked by '"
                                + self.conns[clientid]['name'] + "'")
                            self.sendMsgTo(clientid,
                                           f"Kicked user '{name}', {args}")
                        self.disconnectConn(id)

        def connectto(clientid, args):
            if len(args) == 2:
                try:
                    args[1] = int(args[1])
                except ValueError:
                    self.sendMsgTo(clientid, "Port must be an integer")
                    return
            # Connect to servername
            if len(args) == 1:
                serverid = self.getIDof(username=args[0])
                if serverid is None:
                    self.sendMsgTo(clientid, f"No Connection '{args[0]}'")
                    return
                elif not self.conns[serverid]['isserver']:
                    self.sendMsgTo(clientid, f"Connection '{args[0]}' "
                                       + "is no server")
                    return
                self.sendCommandTo(
                    self.mainSocketof(clientid),
                    'connect',
                    self.conns[serverid]['clientdata']['serveraddr'])
                # server side close if client refuses to disconnect. Since this
                # Function is called through a recv thread this always works
                self.mainSocketof(clientid).close()

            # Connect to address
            else:
                if (args[0], args[1]) == self.addr:
                    self.sendMsgTo(
                        clientid,
                        "You are already connected with this address")
                self.connectionInfo(
                    "'" + self.conns[clientid]['name']
                    + f"' is connecting to {args[0]} at port {args[1]}")
                self.sendCommandTo(self.mainSocketof(clientid),  # type: ignore
                                   'connect', [args[0], args[1]])
                # server side close if client refuses to disconnect. Since this
                # Function is called through a recv thread this always works
                self.mainSocketof(clientid).close()  # type: ignore

        def storelog(clientid, args):
            if not self.logfile == '':
                self.sendMsgTo(
                    clientid, f"Events already get stored in '{self.logfile}'")
                return
            if len(args) == 0:
                self.logfile = f'Serverlog_{self.addr[1]}.txt'
            else:
                self.logfile = args[0]
                if not self.logfile.endswith('.txt'):
                    self.logfile += '.txt'
            self.statusInfo(f"Saving events in '{self.logfile}'")
            self.sendMsgTo(clientid,
                                f"Saving events in '{self.logfile}'")
            with open(self.logfile, 'w') as file:
                for event in self._log:
                    file.write(event)

        def closedatasock(clientid, args):
            for arg in args:
                sockdata = self.getSockData(arg)
                if sockdata is not None:
                    if arg != 'Serversock':
                        self.closeDataSock(arg)
                        self.sendMsgTo(clientid, f"Closed Serversock '{arg}'")
                    else:
                        self.sendMsgTo(
                            clientid, "The 'Serversock' can not be closed")
                else:
                    self.sendMsgTo(clientid,
                                   f"No Datasocket '{arg}' found")

        def restart(clientid):
            cl_data = self.conns[clientid]['data']
            if 'restart_ack' in cl_data \
            and cl_data['restart_ack'] >= time() - 30:
                for connid in self.conns:
                    self.sendMsgTo(connid, f"Server '{self.username}' is "
                                       + "restarting")
                self.restartServer()
                return
            elif 'restart_ack' in cl_data:
                self.sendMsgTo(clientid, "Restart confirmation expired")
            self.conns[clientid]['data']['restart_ack'] = time()
            self.sendMsgTo(clientid, "Confirm restart of server '"
                               + self.username + "' by sending 's.restart()'.")

        def shutdown(clientid):
            cl_data = self.conns[clientid]['data']
            if 'shutdown_ack' in cl_data \
            and cl_data['shutdown_ack'] >= time() - 30:
                for connid in self.conns:
                    self.sendMsgTo(
                        connid,
                        f"\033[1mServer '{self.username}' is shutting down"
                        + "\033[0m")
                self.shutdownServer()
                return
            elif 'shutdown_ack' in cl_data:
                self.sendMsgTo(clientid, "Shutdown confirmation expired")
            self.conns[clientid]['data']['shutdown_ack'] = time()
            self.sendMsgTo(clientid, "Confirm the shutdown of server '"
                               + self.username
                               + "' by sending 's.shutdown()'.")

        def trace(clientid):
            error_trace = ''.join([event for event in self._log if (
                'WARNING' in event or 'ERROR' in event)])
            self.sendMsgTo(clientid,"\033[1mError trace for Server " +
                               f"{self.username}:\033[0m")
            if len(error_trace) > 0:
                self.sendDataTo(self.mainSocketof(clientid),  # type: ignore
                                error_trace)
            else:
                self.sendDataTo(self.mainSocketof(clientid),  # type: ignore
                                "*No problems*")

        def attributes(clientid):
            sendtext = f"\033[1mAttributes of '{self.username}':\033[0m"
            sendtext += "\n  Separator: " + self._se_sep
            sendtext += "\n  Max datasize: " + str(self.se_max_datasize)
            sendtext += "\n\n  Serverdata:"
            if len(self.getServerData()) > 0:
                for key in self.getServerData():
                    sendtext += f"\n    {key}"
            else:
                sendtext += "\n    *No Data*"
            sendtext += "\n\n  ServerRequestables:"
            if len(self.se_requestables) > 0:
                for key in self.se_requestables:
                    sendtext += f"\n    {key}"
            else:
                sendtext += "\n    *No Requestables*"
            self.sendMsgTo(clientid, sendtext)

        def listthreads(clientid):
            infostr = "\033[1mActive threads:\033[0m " + \
                str(len(thread_enumerate()))
            thread_list = [th for th in thread_enumerate() if th.is_alive()]
            thread_list.sort(key=lambda thread_obj: thread_obj.name)
            for thread in thread_list:
                infostr += ("\n  " + thread.name)
            self.sendMsgTo(clientid, infostr)

        def listsocks(clientid):
            sendtext = "\033[1mActive serversocks: (" + \
                str(len(self.serversocks)) + ")\033[0m"
            for (name, entry) in self.serversocks.items():
                port = entry[0].getsockname()[1]
                n_connected = 0
                connected_names = []
                for _, conn in self.conns.items():
                    if port in conn['socks']:
                        n_connected += 1
                        connected_names.append(conn['name'])
                sendtext += (
                    f"\n  {name} ({port})"
                    + f"\n    connected_users ({n_connected}):")
                sendtext += "\n      " + ", ".join(connected_names)
                sendtext += (
                    f"\n    connect_new_clients: {entry[1]}"
                    + f"\n    logging_info: {entry[2]}\n")
            self.sendMsgTo(clientid, sendtext)

        def getrights(clientid, args):
            added = []
            for permission in args:
                if permission not in self.conns[clientid]['permissions'] \
                and permission != '':
                    self.conns[clientid]['permissions'].append(permission)
                    added.append(permission)
            if len(added) > 0:
                if len(added) == 1:
                    self.sendMsgTo(clientid, f"Gained permission: {added[0]}")
                else:
                    self.sendMsgTo(
                        clientid, f"Gained permissions: {', '.join(added)}")
            else:
                self.sendMsgTo(clientid, "No new permissions added")

        def removerights(clientid, args):
            removed = []
            for permission in args:
                if permission in self.conns[clientid]['permissions']:
                    self.conns[clientid]['permissions'].remove(
                        permission)
                    removed.append(permission)
            if len(removed) > 0:
                self.sendMsgTo(
                    clientid,
                    f"Removed permissions: {', '.join(removed)}")
            else:
                self.sendMsgTo(clientid, "No permissions removed")

        def services(clientid, args):
            if len(args) > 1:  #En/-disable a single service
                if args[0].lower() in ('true', '1'):
                    state = True
                elif args[0].lower() in ('false', '0'):
                    state = False
                else:
                    self.sendMsgTo(
                        clientid,
                        f"Invalid argument '{args[0]}', boolean expected")
                    return
                for arg in args[1:]:
                    if arg in self.services:
                        self.setServiceEnabled(arg, state)
                        if state:
                            self.statusInfo(f"Enabled service '{arg}'")
                            self.sendMsgTo(
                                clientid, f"Service '{arg}' is now activated")
                        else:
                            self.statusInfo(f"Disabled service '{arg}'")
                            self.sendMsgTo(
                                clientid,
                                f"Service '{arg}' is now deactivated")
                    else:
                        self.sendMsgTo(clientid, f"No service '{arg}' found")
            else: #En-/disable the service routine
                if args[0].lower() in ('true', '1'):
                    if self.services_active:
                        self.sendMsgTo(clientid, "Service is already active")
                        return
                    else:
                        Thread(target=self.servicesController,
                                        name='Service').start()
                        self.sendMsgTo(clientid,
                                       "Enabled the service function")
                elif args[0].lower() in ('false', '0'):
                    self.services_active = False
                    self.sendMsgTo(clientid, "Disabled service function.")
                else:
                    self.sendMsgTo(
                        clientid,
                        f"Invalid argument '{args[0]}', boolean expected")

        # User management
        self.newServerCommand(
            's.connectto', "Connects the client to another server",
            lambda id, args: connectto(id, args),
            args=['ip'],
            optional_args=['port'],
            category='user management')
        self.newServerCommand(
            's.ping', "Tests connection speed",
            lambda id, args: ping(id),
            call_as_thread=True,
            category='user management')
        self.newServerCommand(
            's.changename', "Changes the username of/for a client",
            lambda id, args: changename(id, args),
            args=['newname'],
            optional_args=['clientname'],
            category='user management')
        self.newServerCommand(
            's.getadmin', "Gives the user admin permissions",
            lambda id, args: getadmin(id, args),
            optional_args=['adminkey'],
            category='user management')
        self.newServerCommand(
            's.removeadmin',
            "Removes admin permissions for the user or another client",
            lambda id, args: removeadmin(id, args),
            optional_args=['username'],
            repeatable_arg='username',
            needed_permission='admin',
            category='user management')
        self.newServerCommand(
            's.mute',
            "Prevents evaluation of messages or data received from a client",
            lambda id, args: mute(id, args),
            repeatable_arg='username',
            needed_permission='admin',
            category='user management')
        self.newServerCommand(
            's.unmute',
            "Enables evaluation of messages or data received from a client",
            lambda id, args: unmute(id, args),
            repeatable_arg='username',
            needed_permission='admin',
            category='user management')
        self.newServerCommand(
            's.kickuser', "Disconnects a user from the server",
            lambda id, args: kickuser(id, args),
            repeatable_arg='username',
            needed_permission='admin',
            category='user management')
        self.newServerCommand(
            's.kickip', "Disconnects every client of an ip address",
            lambda id, args: kickip(id, args),
            repeatable_arg='ip',
            needed_permission='admin',
            category='user management')
        self.newServerCommand(
            's.getrights', "Gives the user permissions",
            lambda id, args: getrights(id, args),
            repeatable_arg='permission',
            needed_permission='admin',
            category='user management')
        self.newServerCommand(
            's.removerights', "Removes permissions from the user",
            lambda id, args: removerights(id, args),
            repeatable_arg='permission',
            needed_permission='admin',
            category='user management')

        # Server management
        self.newServerCommand(
            's.setadminkey', "Changes the key to get admin permissions",
            lambda id, args: setadminkey(id, args),
            args=['new_key'],
            needed_permission='admin',
            category='server management')
        self.newServerCommand(
            's.storelog', "Saves all occurred and future events in a logfile",
            lambda id, args: storelog(id, args),
            optional_args=['filename'],
            needed_permission='admin',
            category='server management')
        self.newServerCommand(
            's.closedatasock', "Closes a serverdatasocket",
            lambda id, args: closedatasock(id, args),
            needed_permission='admin',
            repeatable_arg='serversockname',
            category='server management')
        self.newServerCommand(
            's.restart', "Restarts the Server",
            lambda id, args: restart(id),
            call_as_thread=True,
            needed_permission='admin',
            category='server management')
        self.newServerCommand(
            's.shutdown', "Shuts the server down",
            lambda id, args: shutdown(id),
            call_as_thread=True,
            needed_permission='admin',
            category='server management')
        self.newServerCommand(
            's.services',
            "En-/disable the services routine or a single service",
            lambda id, args: services(id, args),
            args=['enable'],
            optional_args=['service_name'],
            needed_permission='admin',
            category='server management')

        # Server statistics
        self.newServerCommand(
            's.getadminkey', "Shows the adminkey",
            lambda id, args: self.sendMsgTo(id, f"Adminkey: {self.adminkey}"),
            needed_permission='admin',
            category='statistic')
        self.newServerCommand(
            's.help', "Shows available servercommands and how to use them",
            lambda id, args: program_help(id, args),
            optional_args=['servercommand'],
            repeatable_arg='servercommand',
            category='statistic')
        self.newServerCommand(
            's.info',
            description="Shows useful data about the server or a user",
            action=lambda id, args: info(id, args),
            optional_args=['entity_name'],
            repeatable_arg='entity_name',
            category='statistic')
        self.newServerCommand(
            's.errortrace', "Shows error and warning trace",
            lambda id, args: trace(id),
            needed_permission='admin',
            category='statistic')
        self.newServerCommand(
            's.attributes', "Shows useful attributes of the server",
            lambda id, args: attributes(id),
            needed_permission='admin',
            category='statistic')
        self.newServerCommand(
            's.listthreads', "Shows running threads of the server",
            lambda id, args: listthreads(id),
            needed_permission='admin',
            category='statistic')
        self.newServerCommand(
            's.listsocks', "Shows bound sockets of the server",
            lambda id, args: listsocks(id),
            needed_permission='admin',
            category='statistic')

    def _initServerRequestables(self):
        """Defines data that can be requested by a client.

        ...

        Initiated Serverrequestables:
        - SERVERDATA

        ---
        See Also
        --------
        newServerRequestable : creates a new requestable
        """

        self.newServerRequestable('SERVERDATA', lambda: self.getServerData())

    def execServercommand(self, clientid: str, command: str,
                             arguments: Optional[list[Any]] = None):
        """Executes a servercommand sent by a client.

        ...

        Checks if the the *servercommand* exists and has the right
        arguments. Also checks if the client has needed permissions for
        that command. The client gets notified if the command, arguments
        or permissions are invalid. If the command doesn't call a new
        thread, the client also gets notified if an error occurred.

        ---
        Parameters
        ----------
        clientid : str
            ID of a client
        command : str
            Name of the transmitted command
        arguments : list[Any] | None, optional
            Arguments needed to execute the command

        ---
        See Also
        --------
        newServerCommand : Creates a new *servercommand*
        recvClientData : Receives *servercommand* calls from a client

        ---
        Notes
        -----
        - If a `recvClientData` thread receives a *servercommand*,
        this function will be called to execute the command.
        """

        if arguments is None:
            arguments = []
        elif isinstance(arguments, str):
            arguments = []
        if command not in self.se_commands:
            self.sendMsgTo(clientid, f"No Servercommand '{command}' available")
            return

        # Check permissions
        if not (all(needed_permission in self.conns[clientid][
        'permissions'] for needed_permission in
        self.se_commands[command][2])):
            self.sendMsgTo(
                clientid,
                ', '.join(self.se_commands[command][2])
                + f"' permissions needed for '{command}()'")
            return

        # Check valid number of arguments
        n_args = len(self.se_commands[command][3])
        n_o_args = len(self.se_commands[command][4])
        if not (self.se_commands[command][5] is None \
        or self.se_commands[command][5] in self.se_commands[command][4]):
            n_args += 1
        if len(arguments) < n_args:
            self.sendMsgTo(
                clientid,
                "Expecting more arguments: \n  "
                + command + self._getFormattedCommandParams(command))
            return
        elif len(arguments) > n_args + n_o_args \
        and self.se_commands[command][5] is None:
            self.sendMsgTo(
                clientid,
                "Expecting less arguments: \n  "
                + command + self._getFormattedCommandParams(command))
            return

        # Execute
        if self.se_commands[command][1]:
            Thread(
                target=self.se_commands[command][0],
                args=(clientid, arguments,),
                name=f"Servercommand_{command}_" + self.conns[clientid]['name']
            ).start()
        else:
            try:
                self.se_commands[command][0](clientid, arguments)
            except Exception as e:
                self.errorInfo(f"Servercommanderror while executing "
                               + f"'{command}()': {e}")
                self.sendMsgTo(clientid, "Error while executing "
                                   + f"'{command}()'")

    # -----------------+
    # Services routine |
    # -----------------+

    def newService(self, name: str, service_func: Callable,
                   as_thread: bool=False, enabled: bool=True, overwrite=False):
        """Adds a new service to the *services* routine.

        ...

        A service is a background routine for repetitive tasks like
        keeping serverdata up to date. All services get executed every
        few seconds.

        ---
        Parameters
        ----------
        name : str
            Name of the service
        service_func : Callable
            Service function
        as_thread : bool, optional
            Execute the service in a new thread
        enabled : bool, optional
            Service gets executed by the *services* controller
        overwrite : bool, optional
            Overwrite an already existing service

        ---
        See Also
        --------
        delService : Removes a service
        setServiceEnabled : En-/disables a service
        servicesController : Controls the *services* routine

        ---
        Notes
        -----
        - The **service_func** always gets a list with all clientids.
        - If a service throws an error it gets disabled until it is
        enabled again with ``
        - The execution of a service (stated with **enabled**) can be
        changed later on.

        ---
        Examples
        --------
        >>> from datetime import now
        >>> def time_service(clientids):
        ...     for connid in clientids:
        ...         sendMsg(connid, now())
        >>> s.newService('Time', time_service, as_thread=False)
        """

        if name in self.services and not overwrite:
            self.errorInfo(f"Service '{name}' already exists")
            return
        elif name not in self.services and overwrite:
            self.warningInfo(
                f"Creating new service '{name}' since it does not exist")
        self.services[name] = [service_func, as_thread, enabled]

    def delService(self, name: str):
        """Removes a service from the *services* routine.

        ...

        ---
        Parameters
        ----------
        name : str
            Name of the service that gets removed

        ---
        See Also
        --------
        newService : Creates a new service
        setServiceEnabled : En-/disables a service
        servicesController : Controls the *services* routine
        """

        if name in self.services:
            del self.services[name]
        else:
            raise NameError("No service named '{name}'")

    def _initServices(self):
        """Initiates available services.

        ...

        Initiated services:
        - Metadata_update
        - Ping

        See Also
        --------
        newService : Adds a new service to the routine
        """

        def metadata_update_service(clientids):
            for clientid in clientids:
                # Clientdata
                self.conns[clientid]['clientdata'] = self.sendRequestTo(
                    self.mainDataSockof(clientid),
                    'CLIENTDATA')
                # Serverdata
                self.sendCommandTo(
                    self.mainDataSockof(clientid),
                    'updateserverdata',
                    [self.getServerData()])

        def ping_service(clientids):
            for clientid in clientids:
                self.conns[clientid]['ping'] = self.pingSocket(
                    self.mainDataSockof(clientid))

        self.newService('Metadata_update', metadata_update_service)
        self.newService('Ping', ping_service)

    def setServiceEnabled(self, name: str, enable: bool = True):
        """Sets execution in the services routine for a single service.

        ...

        This is a way of temporally en-/disable a single service. The
        state can be changed later on. If a service will never be
        executed it should be deleted.

        Parameters
        ----------
        name : str
            Name of service
        enable : bool, optional
            State if the service should be enabled or disabled

        ---
        See Also
        --------
        newService : Add a new service to *services*
        delService : Remove a service
        servicesController : Controls the *services* routine

        ---
        Notes
        -----
        - A new added service with `newService()` will is enabled by
        default.
        """

        if not isinstance(enable, bool):
            self.warningInfo("Boolean is needed to en-/disable a service")
            return
        self.services[name][2] = enable

    def servicesController(self, routine_pause: float=1.0,
                           services_thread=True):
        """Starts and controls execution of routine services.

        ...

        Executes all initialized services in `self.services`. Some
        services may be called in another thread, other directly through
        the controller. Services that throw an error will be disabled.
        The routine ends if every service is disabled or
        `services_active` is set to False.

        ---
        Parameters
        ----------
        routine_pause : float, optional
            Delay before next routine iteration
        services_thread=True : bool, optional
            Starts the services routine controller in a new thread

        ---
        See Also
        --------
        newService : Add a new service
        delService : Remove a service
        setServiceEnabled : Dis-/enables a service

        ---
        Notes
        -----
        - *Services* are background routines for repetitive tasks like
        synchronizing data.

        ---
        Examples
        --------
        >>> def ping_service():
        ...     for clientid in s.conns:
        ...         s.conns[clientid]['ping'] = s.pingSocket(
        ...             s.mainDataSockof(clientid))
        >>> s.newService('Ping', ping_service)
        >>> s.servicesController(routine_pause = 1)
        >>> # Pings clients every second
        >>> s.services_active = False
        """

        def service_wrapper(service: Callable, name: str):
            try:
                service(tuple(self.conns.keys()))
            except (ConnectionResetError, ConnectionAbortedError, OSError):
               self.logEvent(
                   f"Service '{service.__name__}' couldn't be completed")
            except Exception as e:
               self.errorInfo(f"Error while executing service '{name}': "
                               + f"{e}")
               self.warningInfo(f"Service '{name}' is now disabled")
               self.services[name][2] = False

        if self.services_active:
            self.warningInfo("Services are already running")
            return
        if services_thread:
            Thread(name='services',
                   target=self.servicesController,
                   args=(routine_pause, False,)
            ).start()
            return

        self.services_active = True
        self.statusInfo("Started services")
        while self.se_running and self.services_active:
            # Start thread services
            for name, properties in self.services.items():
                if properties[1] and properties[2]:
                    Thread(
                        target= lambda: service_wrapper(
                            properties[0], name),  # type: ignore
                        name=f'service_{name}'
                    ).start()

            # Execute non-thread services
            for name, properties in self.services.items():
                if not properties[1] and properties[2]:
                    service_wrapper(properties[0], name)  # type: ignore

            # Disable services if every service is disabled
            if all(properties[2] is False for properties in self.services):
                self.services_active = False

            sleep(routine_pause)

        self.statusInfo("Ended services")

    def pingSocket(self, clientsocket: socket) -> float:
        """Measures transmission time for a socket.

        ...

        Measures the time needed to send a request and receive an
        answer from a socket.

        ---
        Parameters
        ----------
        clientsocket : socket
            Socket that gets pinged

        ---
        Returns
        -------
        float : Time needed fulfill a *datarequest* (in seconds)
        float : -0.001 if ping couldn't be determined

        ---
        See Also
        --------
        sendRequestTo : Sends a *datarequest* to a client

        ---
        Notes
        -----
        - A ping of -0.001 is returned, if the request wasn't answered.
        - Can be used with the servercommand 's.ping()'.
        """

        # Essentially a request with an improved timer
        ping = self.sendRequestTo(clientsocket, 'PING', 1, True)
        return -0.001 if isinstance(ping, type(None)) else ping[1]

    # -----------------+
    # Getter functions |
    # -----------------+

    def getSocketof(self, id: str, port: int) -> socket:
        """Gets a socket of a client.

        ...

        ---
        Parameters
        ----------
        id : str
            ID of a client

        ---
        Returns
        -------
        socket : Socket of **id** connected to **port**.
        None : No client **id** or **id** not connected to **port**.

        ---
        See Also
        --------
        mainSocketof : Gets a socket connected to the *serversock*
        mainDataSockof : Gets a socket connected to the *maindatasock*
        getIDof : Gets the ID of a client

        """

        try:
            return self.conns[id]['socks'][port]
        except KeyError:
            return None  # type: ignore

    def mainSocketof(self, id: str) -> socket:
        """Gets a client socket connected with the *serversock*.

        ...

        Returns the server side socket for a client **id** connected to
        the *serversock*.

        ---
        Parameters
        ----------
        id : str
            ID of a client

        ---
        Returns
        -------
        socket : Socket of **id** connected to the serversock
        None : No client **id** connected

        ---
        See Also
        --------
        getSocketof : Gets a socket of a client

        ---
        Notes
        -----
        - This function shortens `self.conns[id]['socks'][self.addr[1]]`
        and prevents KeyErrors.

        ---
        Examples
        --------
        >>> s.mainDataSockof(getIDof(username='con1'))
        <socket ... >
        """

        return self.getSocketof(id, self.addr[1])

    def mainDataSockof(self, id: str) -> socket:
        """Gets the client socket connected with the *maindatasock*.

        ...

        Returns the server side socket for a client **id** connected to
        the *maindatasock* or the *serversock* if no *maindatasock* is
        initialized.

        ---
        Parameters
        ----------
        id : str
            ID of a client

        ---
        Returns
        -------
        socket : Socket of client **id** that is mainly used for
            background data transmissions.
        None : No client with **id** exists

        ---
        See Also
        --------
        getSocketof : Gets a socket of a client

        ---
        Notes
        -----
        - This function shortens the phrase
        `self.conns[id]['socks'][self.getMainDataPort()]`.
        """

        return self.getSocketof(id, self.getMainDataPort())

    def getIDof(self, username: Optional[str] = None,
                 socket: Optional[socket] = None,
                 addr: Optional[tuple[str, int]] =  None) -> str:
        """Gets the ID of a client with one certain property.

        ...

        ---
        Parameters
        ----------
        username : str | None, optional
            Username of a client
        socket : socket | None, optional
            Socket of a client
        addr : tuple[str, int] | None, optional
            Ip and port of a client

        ---
        Returns
        -------
        str : ID of the client with the given property
        None : No client with the given property found

        ---
        Notes
        -----
        - Only one argument is needed to get the ID.

        ---
        Examples
        --------
        >>> s.getIDof(username='client_1')
        '1c3e6f7a-b8c0-4b1b-9c6c-d1d2e3f4f5f6'
        """

        if (username, socket, addr).count(None) < 2:
            self.warningInfo(
                "Only one argument should be passed to get the ID of a client")
        for connid in self.conns:
            if username is not None \
            and self.conns[connid]['name'] == username:
                return connid
            elif socket is not None:
                for port in self.conns[connid]['socks']:
                    if self.conns[connid]['socks'][port] == socket:
                        return connid
            elif addr is not None:
                if isinstance(addr, tuple) \
                and self.conns[connid]['addr'] == addr:
                    return connid
                else:  # Only ip given
                    if self.conns[connid]['addr'][0] == addr \
                    and isinstance(addr, str):
                        return connid
        return None  # type: ignore

    def getMainDataPort(self) -> int:
        """Gets the port of the sock used for background transmissions.

        ...

        If a *maindatasock* is used for background transmissions, its
        port will be returned. Otherwise, the port of the *serversock*
        gets returned.

        ---
        Returns
        -------
        int : port of the sock used for background transmissions

        ---
        See Also
        --------
        getSockData : Gets data of a sock through a property of it
        """

        if self.getSockData('Maindata') is not None:
            return self.getSockData('Maindata')[0].getsockname()[1]
        else:
            return self.serversocks['Serversock'][0].getsockname()[1]

    def getSockData(self, name: Optional[str] = None,
                    sock: Optional[socket] = None,
                    port: Optional[int] = None
                    ) -> tuple[socket, bool, bool, str]:
        """Gets data of a serversock through one property of it.

        ...

        ---
        Parameters
        ----------
        name : str, optional
            Name of a serversock
        sock : socket, optional
            Socket obj of a serversock
        port : int, optional
            Port of a serversock

        ---
        Returns
        -------
        tuple : Entry in *serversocks* and its name
                -> tuple[socket, connect_new_clients, show_info, name]
        None : No serversock with that property

        ---
        See Also
        --------
        getMainDataPort : Get the port of the sock

        ---
        Notes
        -----
        - Only one property is required

        ---
        Examples
        --------
        >>> s.getSockData('Serversock')
        [<socket...>, True, True]  # [sock, connect_new, show_info]

        >>> s.getSockData('Maindatasock')
        [<socket...>, True, False]

        """

        for sockname, sockdata in self.serversocks.items():
            if sockname == name \
            or sockdata[0] == sock \
            or sockdata[0].getsockname()[1] == port:
                sockdata = sockdata + (sockname,)
                return sockdata
        return None  # type: ignore

    def getServerData(self) -> dict[str, object]:
        """Gets metadata of the server that is useful to a client.

        ...

        ---
        Returns
        -------
        dict[str, object] : Values of the server with following keys:
        - servername
        - description
        - version
        - starttime
        - layer
        - separator
        - max_datasize
        - servercommands
        - requestables
        - socks

        ---
        Notes
        -----
        - *Serverdata* gets sent to a client during registration and
        is continuously transmitted if *services* are active.
        - Serverdata can be listed with the 's.attributes()'
        servercommand.
        """

        sock_entry = [[n, self.serversocks[n][0]] for n in self.serversocks]
        return {'servername': self.username,
                'description': self.description,
                'server_version': Server.__version__,
                'starttime': self._starttime,
                'layer': self.layer,
                'separator': self._se_sep,
                'max_datasize': self.se_max_datasize,
                'max_username_length': self._max_username_length,
                'servercommands': list(self.se_commands.keys()),
                'requestables': list(self.se_requestables.keys()),
                'socks': [[n, sock.getsockname()[1]] for n, sock in sock_entry]
                }

    @staticmethod
    def _generateNewConnID() -> str:
        """Generates a unique identification key for a connection.

        ...

        ---
        Returns
        -------
        str : new identification key
        """

        return str(uuid4())

    @staticmethod
    def _generateTransmissionID() -> str:
        """Generates an id for a data transmission.

        ...

        ---
        Returns
        -------
        str : new id

        ---
        Notes
        -----
        - This is especially needed when large data gets split and
        transmitted into multiple *packets*.
        """

        return str(uuid4())

    @staticmethod
    def _generateRequestID() -> str:
        """Generates a key for data requests.

        ...

        ---
        Returns
        -------
        str : generated key
        """

        return str(uuid4())

    def _parse_port_expression(self, port_expression: int | str | Iterable[int]
                               ) -> Iterable[int]:
        """Formats preferred/allowed ports into an iterable.

        ...

        ---
        Parameters
        ----------
        port_expression : int | str | Iterable

        ---
        Returns
        -------
        Iterable[int]: List with allowed port as per expression

        ---
        Notes
        -----
        - This does not check if the ports in the returned list are
        useable or exist (Possible ports are 0-65535).

        ---
        Examples
        --------
        >>> s._parse_port_expression(4000)
        [4000]

        >>> s._parse_port_expression([4000, 4002])
        [4000, 4002]

        >>> s._parse_port_expression('>4000')
        count(4000)  # itertools object
        """

        if isinstance(port_expression, int):
            port_expression = [port_expression]
        elif isinstance(port_expression, str) and port_expression[0] == '=':
            port_expression = [int(port_expression[1:])]
        elif isinstance(port_expression, str) and port_expression[0] == '>':
            port_expression = count(start=int(port_expression[1:]))
        elif isinstance(port_expression, str) and port_expression[0] == '<':
            port_expression = count(start=int(port_expression[1:]), step=-1)
        elif not isinstance(port_expression, Iterable) \
        or isinstance(port_expression, str):
            try:
                port_expression = [int(port_expression)]
            except Exception:
                 raise ValueError(
                f"'{port_expression}' is an invalid input port expression")
        return port_expression

    def _getFormattedCommandParams(self, commandname: str) -> str:
        """Returns formatted parameters of a servercommand.

        ...

        This uses the cosmetic parameters of a servercommand and
        formats them into a readable string.

        ---
        Parameters
        ----------
        commandname : str
            Name of a servercommand

        ---
        Returns
        -------
        str : Formatted information of a servercommand
        str : '(*No info*)' if command does not exist

        ---
        See Also
        --------
        newServerCommand : Sets the parameters for a servercommand

        ---
        Notes
        -----
        - Used for the 's.help()' servercommand.
        - Optional parameters are marked with *[o]* and repeatable ones
        with *[r]*.

        ---
        Examples
        --------
        >>> s.newServerCommand('s.paint',
        ...    "Paints symbols on a surface", ...,
        ...     args=['surface'],
        ...     repeatable_arg='symbol')
        >>> s._getFormattedCommandParams('s.paint')
        (surface, symbol[r])

        >>> s.newServerCommand('s.free_drinks',
        ...    "Give out free drinks", ...,
        ...     repeatable_arg='drink_name')
        >>> s._getFormattedCommandParams('s.free_drinks')
        (drink_name[r])

        >>> s.newServerCommand('s.address',
        ...    "Saves an address for a person", ...,
        ...     args=['name', 'street', 'house_nr'],
        ...     optional_args=['apartment_nr', 'phone_nr'],
        ...     repeatable_arg='phone_number')
        >>> s._getFormattedCommandParams('s.address')
        (name, street, house_nr, apartment_nr[o], phone_nr[o][r])
        """

        if commandname not in self.se_commands:
            return "(*No info*)"
        all_args = list(self.se_commands[commandname][3:6])
        all_args[1] = [f'{o_arg}[o]' for o_arg in all_args[1]]
        if f"{all_args[2]}[o]" in all_args[1]:
            all_args[1][-1] += '[r]'
        elif all_args[2] is not None:
            all_args[1].append(f"{all_args[2]}[r]")
        return f"({', '.join(all_args[0] + all_args[1])})"  # type: ignore

    def _get_infotext_server(self, admin_text: bool) -> str:
        """Returns an informational text about the server state.

        ...

        This text gets send to a client when the *s.info()*
        servercommand is called.

        ---
        Parameters
        ----------
        admin_text : bool
            Returns additional information for admins

        ---
        Returns
        -------
        str: *ANSI* and line formatted text about the server state
        """

        info_text = "\033[1;4mSERVERINFO\033[0;1m:\033[0m"
        info_text += ("\n  name: " + self.username
                    + "\n  description: " + self.description
                    + "\n  server version: " + Server.__version__
                    + "\n  runtime: "
                    + str(int((time() - self._starttime) / 60))
                    + "min"
                    + "\n\n  ip: " + self.addr[0]
                    + "\n  port: " + str(self.addr[1])
                    + "\n  network layer: " + str(self.layer))
        if admin_text:
            info_text += "\n\n  \033[1mSERVICES:\033[0m"
            if not self.services_active:
                info_text += "\n    "
                info_text += "\033[3mServices routine is not running\033[0m"
            else:
                for name, prop in self.services.items():
                    info_text += f"\n    {name}: "
                    if prop[2]:
                        info_text += "enabled"
                        if prop[1]:
                            info_text += " (called as thread)"
                    else:
                        info_text += "disabled"
            info_text += "\n\n  \033[1mTHREADS:\033[0m " + str(
                len([th for th in thread_enumerate() if th.is_alive()]))
            thread_list = thread_enumerate()
            thread_list.sort(key=lambda thread_obj: thread_obj.name)
            for thread in thread_list:
                info_text += ("\n    " + thread.name +
                              "  running" if thread.is_alive() else "")
            info_text += "\n\n  SOCKETS: " + str(len(self.serversocks))
            for sockname, sockdata in self.serversocks.items():
                info_text += (f"\n    {sockname}("
                            + str(sockdata[0].getsockname()[1])
                            + f")  new_clients: {sockdata[1]}")
        info_text += f"\n\n  \033[1mCONNECTIONS:\033[0m {len(self.conns)}"
        for conn in self.conns:
            conn = self.conns[conn]
            info_text += (f"\n    {conn['name']}({conn['addr'][0]})  "
                          + f"{int((time()-conn['connecttime'])/60)}min  "
                          + f"{int(conn['ping'] * 1000)}ms")
        return info_text

    def _get_infotext_user(self, username: str) -> str:
        """Returns a text with information about a user.

        ...

        This text gets send to a client when the *s.info()*
        servercommand is called with a *username* parameter.

        ---
        Parameters
        ----------
        username : str
            Returns information about the connection with this username

        ---
        Returns
        -------
        str: *ANSI* and line formatted text about a user
        str: Empty string if user doe
        """

        id = self.getIDof(username)
        if id is None:
            return ""
        conn_data = self.conns[id]
        return ("\033[1;4mUSERINFO\033[0;1m:\033[0m"
            + "\n  username: " + conn_data['name']
            + "\n  ip: " + conn_data['addr'][0]
            + "\n  server: " + str(conn_data['isserver'])
            + "\n  description: "
            + conn_data['clientdata']['description']
            + "\n\n  permissions: "
            + ", ".join(conn_data['permissions'])
            + "\n  active sockets: "
            + ", ".join([ str(key) for key in conn_data['socks'].keys()])
            + "\n  muted: " + str(conn_data['muted'])
            + "\n\n  ping: " + str(int(conn_data['ping'] * 1000))
            + "ms"
            + "\n  connecttime: "
            + str(int((time()-conn_data['connecttime']) / 60))
            + "min"
            + "\n  layer: " + str(self.layer+1))

    def __str__(self) -> str:
        """Values returned when converting to string.

        ...

        ---
        Returns
        -------
        str : `Server` object formatted to string
        """

        returned = f"Server ({self.username}), "
        returned += "active" if self.se_running else "inactive"
        for sock in self.serversocks.keys():
            returned += f", {sock}={self.serversocks[sock][0].getsockname()}"
        return f"<{returned}>"

    # ---------------------+
    # Displaying functions |
    # ---------------------+

    def printInfo(self, message: str, sender: str=""):
        """Outputs a client message.

        ...

        ---
        Parameters
        ----------
        message : str
            Text that gets outputted
        sender : str, optional
            Username of the client that sent the message

        ---
        See Also
        --------
        connectionInfo : Outputs a connection information
        statusInfo : Outputs a state of the server
        warningInfo : Outputs a warning
        errorInfo : Outputs an error
        logEvent : Logs an events

        ---
        Notes
        -----
        - The messages get received on the serversock.
        - If *ANSI* formatting is enabled, the message can be colored.
        """

        if sender != "":
            message = f"\033[1;4m{sender}\033[0;1m\033[0m{message}"
        if not self._ansi:
            message = compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])').sub(
                              '', message)
        print(message)
        self.logEvent(message)

    def connectionInfo(self, info: str):
        """Outputs information regarding connections.

        ...

        ---
        Parameters
        ----------
        info : str
            Connection information

        ---
        See Also
        --------
        printInfo : Outputs a client message
        statusInfo : Outputs a state of the server
        warningInfo : Outputs a warning
        errorInfo : Outputs an error
        logEvent : Logs an events

        ---
        Notes
        -----
        - If *ANSI* is allowed, the printed info gets colored.
        """

        if self._ansi:
            print(f"\033[38;5;230m{info}\033[0m")
        else:
            info = compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])').sub(
                           '', info)
            print(info)
        self.logEvent(f"CONNECTION: {info}")

    def statusInfo(self, status: str):
        """Outputs states of the server and logs the event.

        ...

        ---
        Parameters
        ----------
        status : str
            Status text that gets outputted

        ---
        See Also
        --------
        printInfo : Outputs a client message
        connectionInfo : Outputs a connection information
        warningInfo : Outputs a warning
        errorInfo : Outputs an error
        logEvent : Logs an events

        ---
        Notes
        -----
        - If *ANSI* codes are allowed the status will be displayed gray.
        """

        if self._ansi:
            print(f"\033[38;5;243m{status}\033[0m")
        else:
            status = compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])').sub(
                             '', status)
            print(status)
        self.logEvent(f"STATUS: {status}")

    def warningInfo(self, warning: str):
        """Outputs a warning and logs the event.

        ...

        ---
        Parameters
        ----------
        warning : str
            Warning Information that gets outputted

        ---
        See Also
        --------
        printInfo : Outputs a client message
        connectionInfo : Outputs a connection information
        statusInfo : Outputs a state of the server
        errorInfo : Outputs an error
        logEvent : Logs an events

        ---
        Notes
        -----
        - If *ANSI* formatting is allowed, the warning will be orange.
        """

        if self._ansi:
            print("\033[38;5;214m\033[1;4mWAR:\033[0;1m\033[38;5;214m " + \
                  warning + "\033[0m")
        else:
            warning = compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])').sub(
                              '', warning)
            print(f"WAR: {warning}")
        self.logEvent(f"WARNING: {warning}")

    def errorInfo(self, error: str):
        """Outputs an error and logs the event.

        ...

        ---
        Parameters
        ----------
        error : str
            Error information that gets outputted

        ---
        See Also
        --------
        printInfo : Outputs a client message
        connectionInfo : Outputs a connection information
        statusInfo : Outputs a state of the server
        warningInfo : Outputs a warning
        logEvent : Logs an events

        ---
        Notes
        -----
        - If *ANSI* formatting is allowed, the error gets colored red.
        """

        if self._ansi:
            print(f"\033[91;1;4mERR:\033[0;1;91m {error}\033[0m")
        else:
            error = compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])').sub(
                            '', error)
            print(f"ERR: {error}")
        self.logEvent(f"ERROR: {error}")

    def logEvent(self, event: str):
        """Saves events and writes them into a logfile (if available).

        ...

        ---
        Parameters
        ---------
        event : str
            Event information that gets stored

        ---
        See Also
        --------
        printInfo : Outputs a client message
        connectionInfo : Outputs a connection information
        statusInfo : Outputs a state of the server
        warningInfo : Outputs a warning
        errorInfo : Outputs an error

        ---
        Notes
        -----
        - All implemented outputs log their events.
        """

        event = compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])').sub('',
                        event)
        event = f"{datetime.now().strftime('%H:%M:%S:%f')}>  {event}\n"
        self._log.append(event)
        if self.logfile != '':
            with open(self.logfile, 'a') as log:
                log.write(event)
        # Warn about log size
        if len(self._log) % 10_000 == 0 and len(self._log) > 200_000:
            if not self.logfile == '':
                self._log = []
                self.statusInfo(
                    f"Clearing internal log (size: {len(self._log)}) since "
                    + f"events get stored to '{self.logfile}'")
            else:
                self.warningInfo(
                    "Log holds many entries. Consider storing to a file.")


class SubServer(Server, Client):
    """Node server for multi layer networks.

    ...

    A `SubServer` is the combination of a `Client` and a `Server` used
    as a network node. Clients can connect to it *(like to a server)*
    and itself can connect to other servers *(like a client)*. The
    server a subserver connects to is referred to as the *higher
    server*. Subserver provide additional *client-/servercommands* and
    *requestables*.

    When extending the SubServer class, all arguments of the new class
    constructor must be passes to the SubServer constructor.

    ---
    Attributes
    ----------
    *`Client` inherited attributes*
    *`Server` inherited attributes*

    ---
    Notes
    -----
    - To distinguish between similar attributes of server and client,
    server attributes start with 'se_*' and client attributes start
    with 'cl_*'.
    """

    __version__ = '4.17.075'

    def __init__(self, servername: str = 'subserver',
                 preferredport: int | str | Iterable = '>4000',
                 preferreddataport: int | str | Iterable ='<3999',
                 max_datasize: int = 2048, adminkey: str = '',
                 description: str = "None", logfile: str = '',
                 ansi :bool = True, *args,**kwargs):
        """...

        ---
        Parameters
        ----------
        servername : str
            Name of the subserver
        preferredport : int | str | Iterable
            Allowed ports to bind the server to
        preferreddataport : int | str |Iterable
            Allowed ports to bind datasocks to
        max_datasize : int
            Maximum bytes size of one transmission
        adminkey : str
            Key for admin permissions
        description : str
            Short description of the subserver
        logfile : str
            Path to file that stores occurred events
        ansi : bool
            Allow *ANSI* text formatting

        ---
        See Also
        --------
        network.Server.__init__ : initialization of `Server` object

        ---
        Notes
        -----
        - *Datasocks* apart from the mainly used *serversock*, are used
        for custom data transmissions.
        """

        Client.__init__(
            self,
            username=servername,
            description=description,
            logfile='',
            ansi=ansi)
        Server.__init__(
            self,
            servername=servername,
            preferredport=preferredport,
            preferreddataport=preferreddataport,
            adminkey=adminkey,
            description=description,
            max_datasize=max_datasize,
            logfile=logfile,
            ansi=ansi,
            args=args,
            kwargs=locals() | kwargs)
        self._conntype = 'SUBSERVER'

        SubServer._initClientRequestables(self)
        SubServer._initClientcommands(self)
        SubServer._initServercommands(self)

    def startServer(self, port: int | str | Iterable[int] = 'preferred',
                    dataport: int | str | Iterable = 'preferred',
                    maindatasock: bool = False, services: bool = True):
        """Binds the subserver and starts all services.

        ...

        The main sock of the server *(serversock)* gets bound to the
        preferred- or another free port. Additionally, the *maindatasock*
        for background data transfer can be initiated. If set,
        *services* get started.

        ---
        Parameters
        ----------
        port : int | str | Iterable[int], optional
            Allowed ports to bind the serversock to
        dataport : int | str | Iterable[int], optional
            Allowed ports to bind datasocks to
        maindatasock : bool, optional
            Initiate the *Maindatasock* with sever start
        services : bool, optional
            Start routine services

        ---
        See Also
        --------
        Server.startServer : Starts a server
        Server.servicesController : Controls services
        """

        if self.se_running:
            self.statusInfo("Subserver is already running")
            return
        Server.startServer(self, port, dataport, maindatasock, services)
        self.statusInfo(f"Subserver '{self.username}' operational")

    def shutdownServer(self):
        """Disconnects the *higher server* and shuts the server down.

        ...

        ---
        See Also
        --------
        Server.shutdownServer : Shuts a server down

        """

        self.statusInfo("Disconnecting from higher server")
        self.disconnect()
        Server.shutdownServer(self)

    def _initClientRequestables(self):
        """Adds *requestables* of the subserver.

        ...

        Initiated clientrequestables:
        - LISTNETWORK

        ---
        See Also
        --------
        Client._initClientRequestables : Initiates client *requestables*

        ---
        Notes
        -----
        - This does not initiate any requestables of the parent class
        `Client`.
        - Client *requestables* are called by the *higher server*.
        - The server/subserver also has (server) *requestables* which
        can be called by clients.
        """

        def listnetwork():
            structure = ['', [], []]
            for connid in self.conns:
                if self.conns[connid]['isserver']:
                    structure[1].append(self.sendRequestTo(
                        self.mainDataSockof(connid), 'LISTNETWORK', 2))
                else:
                    structure[2].append('{}({})'.format(
                        self.conns[connid]['name'],
                        self.conns[connid]['addr'][0]))
            structure[0] = "{}({})  {} servers  {} clients".format(
                self.username,
                self.addr[0],
                len(structure[1]),
                len(structure[2]))
            return structure

        self.newClientRequestable('LISTNETWORK', lambda: listnetwork())

    def _initClientcommands(self):
        """Adds subserver clientcommands.

        ...

        Initiated clientcommands:
        - restart
        - shutdown
        - shutdownnetwork

        Overwritten clientcommands:
        - setlayer

        ---
        See Also
        --------
        Client._initClientcommands : Initiates client commands

        ---
        Notes
        -----
        - This does not initiate any clientcommand of the parent class
        `Client`.
        - These commands get called by the *higher server*.
        """

        def setlayer(layer):
            port = self.getMainDataPort()
            self.layer = layer
            for connid in self.conns:
                self.sendCommandTo(self.conns[connid]['socks'][port],
                                   'setlayer', self.layer + 1)

        def shutdownNetwork():
            port = self.getSockData('Serversock')
            port = port[0].getsockname()[1]
            for clientid in self.conns:
                conn = self.conns[clientid]
                if conn['isserver']:
                    self.sendCommandTo(conn['socks'][port], 'shutdownnetwork')
                else:
                    self.sendCommandTo(conn['socks'][port], 'disconnect')
            self.shutdownServer()

        self.newClientCommand('setlayer', setlayer,
                              overwrite=True)
        self.newClientCommand('restart', self.restartServer,
                              call_as_thread=True)
        self.newClientCommand('shutdown', self.shutdownServer,
                              call_as_thread=True)
        self.newClientCommand('shutdownnetwork', shutdownNetwork)

    def _initServercommands(self):
        """Adds servercommands of the subserver.

        ...

        Initiated servercommands:
        *([o]: optional arguments, [r]: repeatable argument)*
        - s.connecttohigher()
        - s.sethigherserver(ip, port)
        - s.info(username[o][r]), overwritten
        - s.attributes(), overwritten

        ---
        See Also
        --------
        Server._initServercommands : Initiates `Server` servercommands

        ---
        Notes
        -----
        - This does not initiate any servercommand of the parent class
        `Server`.
        - These commands can be called by clients.
        """

        def connecttohigher(clientid):
            if self.connected:
                self.sendCommandTo(self.mainSocketof(clientid), 'connect',
                                   self.connected_addr)
                # server side close if client refuses to disconnect. Since this
                # Function is called through a recv thread this always works
                self.mainSocketof(clientid).close()
            else:
                self.sendMsgTo(
                    clientid, "Subserver has no connected higher server")

        def sethigherserver(clientid, args):
            try:
                args[1] = int(args[1])
            except ValueError:
                self.sendMsgTo(clientid, "Port must be an integer")
                return
            if args == self.addr:
                self.sendMsgTo(clientid, "Can't connect to own address")
                return
            cl_data = self.conns[clientid]['data']
            if not self.connected \
            or 'connect_higher_ack' in cl_data \
            and cl_data['connect_higher_ack'] >= time() - 30.0:
                connect_status = self.connect((args[0], int(args[1])))
                if connect_status == 'Connected':
                    self.sendMsgTo(
                        clientid, "Server connected to higher Server '"
                        + self.cl_serverdata['servername'] + "'")
                else:
                    self.sendMsgTo(clientid, "Connect result: "
                                   + connect_status)
                return
            elif 'connect_higher_ack' in cl_data:
                self.sendMsgTo(
                    clientid,
                    "The Server is currently connected to '"
                    + self.cl_serverdata['servername'] + "'")
            self.conns[clientid]['data']['connect_higher_ack'] = time()
            self.sendMsgTo(
                clientid,
                "Confirm connecting to a new address by sending "
                + f"'s.sethigherserver({args[0]}, {args[1]})'")

        def info(clientid, args):
            # Info of servers
            if len(args) == 0:
                text = self._get_infotext_server(
                    'admin' in self.conns[clientid]['permissions'])

                text = text.split("\n\n")
                if self.connected:
                    text.insert(2,
                        "  Higher server: " + self.cl_serverdata['servername']
                        + "\n  Higher addr: " + str(self.connected_addr))
                else:
                    text.insert(2,
                                "  Higher server: \033[1mNot connected\033[0m")
                text = "\n\n".join(text)

                self.sendMsgTo(clientid, text)

            # Info of entity (user, services, commands)
            else:
                for a in args:
                    conn = self.getIDof(username=a)
                    if a in ['commands', 'servercommands']:
                        self.se_commands['s.help'][0](['commands'])
                    elif conn is not None:
                        self.sendMsgTo(clientid, self._get_infotext_user(a))
                    else:
                        self.sendMsgTo(clientid, f"No user '{a}'")

        def attributes(clientid):
            sendtext = f"\033[1mAttributes of '{self.username}':\033[0m"
            sendtext += "\n  Separator: " + self._se_sep
            sendtext += "\n  Max datasize: " + str(self.se_max_datasize)
            sendtext += "\n\n  Serverdata:"
            if len(self.getServerData()) > 0:
                for key in self.getServerData():
                    sendtext += f"\n    {key}"
            else:
                sendtext += "\n    *No Data*"
            sendtext += "\n\n  ServerRequestables:"
            if len(self.se_requestables) > 0:
                for key in self.se_requestables:
                    sendtext += f"\n    {key}"
            else:
                sendtext += "\n    *No Requestables*"
            sendtext += "\n\n  ClientRequestables:"
            if len(self.cl_requestables) > 0:
                for key in self.cl_requestables:
                    sendtext += f"\n    {key}"
            else:
                sendtext += "\n    *No Requestables*"
            self.sendMsgTo(clientid, sendtext)

        # User management
        self.newServerCommand(
            's.connecttohigher',
            "Connects the client to the higher server layer",
            lambda id, args: connecttohigher(id),
            category='user management')
        self.newServerCommand(
            's.cth',
            "Short form of 's.connecttohigher'",
            lambda id, args: connecttohigher(id),
            category='user management')

        # Server management
        self.newServerCommand(
            's.sethigherserver', "Connects the server to a higher server",
            lambda id, args: sethigherserver(id, args),
            args=['ip', 'port'],
            needed_permission='admin',
            category='server management')

        # Server statistics
        self.newServerCommand(
            's.info', "Shows server or user information",
            lambda id, args: info(id, args),
            optional_args=['username'],
            repeatable_arg='username',
            category='statistic',
            overwrite=True)
        self.newServerCommand(
            's.attributes', "Shows useful attributes of the server",
            lambda id, args: attributes(id),
            needed_permission='admin',
            category='statistic',
            overwrite=True)

    # -----------------------------+
    # Connect and interact methods |
    # -----------------------------+

    def disconnect(self):
        """Terminates connection with the higher server.

        ...

        ---
        See Also
        --------
        Client.disconnect : Disconnects the client from a server
        """

        if self.connected:
            self.statusInfo("Disconnecting from higher Server")
        Client.disconnect(self)

    def connect(self, addr: tuple[str, int] = ('', -1),
                autoconnect: bool = False, timeout: float = 1.0) -> str:
        """Connects the subserver to a *higher server*.

        ...

        ---
        Parameters
        ----------
        addr : tuple[str, int], optional
            Address (ip, port) of the server to connect to
        autoconnect : bool, optional
            Use 'known' server addresses to connect to
        timeout : float, optional
            Abandon connect attempt after n seconds

        ---
        Returns
        -------
        str : A string from `Client.connect()`

        ---
        See Also
        --------
        Client.connect : Connects the client with a server

        ---
        Notes
        -----
        - Addresses of 'known' servers for *autoconnect* can be gained
        with `searchForServer()` and are stored in the
        **autoconnect_addrs** list.

        ---
        Examples
        --------
        >>> ss.connect(autoconnect=True)

        >>> ss.connect(('192.168.178.140', 4000))

        >>> ss.connect((192.168.178.140, 4001), True, 1.5)
        """

        if not self.se_running:
            return 'Server is not started'
        if addr == self.addr:
            return "Can't connect to own address"
        info = Client.connect(self, addr, autoconnect, timeout)
        if info == 'Connected':
            for connid in self.conns:
                self.sendCommandTo(self.mainDataSockof(connid), 'setlayer',
                                   [self.layer + 1])
        return info

    def recvServerMessage(self):
        """Receives messages from the *higher server*.

        ...

        See Also
        --------
        Client.recvServerMessage : Receives messages from a server
        """

        Client.recvServerMessage(self)
        for connid in self.conns:
            self.sendMsgTo(connid, "Lost connection with higher Server")

    def recvUserMessages(self, clientid: str, sock: socket):
        """Receives data from a clientsocket.

        ...

        ---
        Parameters
        ----------
        clientid : str
            ID of a connected client
        sock : socket
            A client socket that is connected to the serversock.

        ---
        See Also
        --------
        Server.recvUserMessages : Receives data on the serversock.
        """

        if not self.connected:
            self.sendMsgTo(
                clientid,
                f"SubServer '{self.username}' is not connected to a higher "
                + "Server")
        Server.recvUserMessages(self, clientid, sock)

    # -----------------+
    # Getter functions |
    # -----------------+

    def getServerData(self) -> dict:
        """Appends serverdata that is useful to clients.

        ...

        ---
        Returns
        -------
        dict : Different server attributes

        ---
        See Also
        --------
        Server.getServerData : Returns data useful to clients
        """

        data = Server.getServerData(self)
        data['higher_addr'] = self.connected_addr
        return data

    def getClientData(self) -> dict:
        """Returns data that is sent to the higher server.

        ...

        ---
        Returns
        -------
        dict : Different subserver attributes

        ---
        See Also
        --------
        Client.getClientData : Different client attributes
        """

        data = {'serveraddr': self.addr}
        return Client.getClientData(self) | data


class MainServer(Server):
    """Root server of a network with additional management tools.

    ...

    Essentially a normal Server with additional commands and tools.

    ***(The MainServer is currently a POC and does not provide a lot of
    features)***

    ---
    Attributes
    ----------
    *`Server` inherited attributes*

    ---
    See Also
    --------
    network.Server : Fundamental Class for interactions with a client

    ---
    Notes
    -----
    - Mainserver should preferably run on port **4000**.
    """

    __version__ = '2.09.040'

    def __init__(self, preferredport: int | str | Iterable[int] = 4000,
                 preferreddataport: int | str | Iterable[int] = '<3999',
                 max_datasize: int = 4096, adminkey: str = '',
                 logfile: str = '', ansi :bool = True):
        """...

        ---
        Parameters
        ----------
        preferredport : int | str | Iterable[int], optional
            Allowed ports to bind the mainserver to
        preferreddataport : int |str | Iterable[int], optional
            Allowed ports to bind datasocks to
        max_datasize : int, optional
            Maximum size of one transmission
        adminkey : str, optional
            Password to gain admin permissions
        logfile : str
            Path of file that stores occurred events
        ansi : bool
            Allow *ANSI* text formatting

        ---
        See Also
        --------
        network.Server.__init__ : Initializes a Server object
        """

        Server.__init__(
            self,
            servername='Mainserver',
            preferredport=preferredport,
            preferreddataport=preferreddataport,
            adminkey=adminkey,
            description="Main control node",
            max_datasize=max_datasize,
            logfile=logfile,
            ansi=ansi
        )

        MainServer._initServercommands(self)
        self.logEvent(f"Mainserver ({MainServer.__version__}) loaded")

    def _initServercommands(self):
        """Initiates additional mainserver servercommands.

        ...

        Initiated servercommands:
        *([o]: optional arguments, [r]: repeatable argument)*
        - s.listnetwork()
        - s.restartserver(serverusername[r])
        - s.shutdownserver(serverusername[r])
        - s.shutdownnetwork()

        ---
        See Also
        --------
        network.Server.newServerCommand : Creates a new servercommand.

        ---
        Notes
        -----
        - This does not initiate any servercommand of the parent class
        `Server`.
        """

        def listnetwork(clientid):
            self.sendMsgTo(clientid, "Collecting data...")

            # Collect network structure
            structure = ['', [], []]  # server, subserver, clients
            for connid in self.conns:
                if self.conns[connid]['isserver']:
                    structure[1].append(self.sendRequestTo(
                        self.mainDataSockof(connid), 'LISTNETWORK', 2))
                else:
                    structure[2].append("{}({})".format(
                        self.conns[connid]['name'],
                        self.conns[connid]['addr'][0]))
            structure[0] = "{}({})  {} servers  {} clients".format(
                self.username,
                self.addr[0],
                len(structure[1]),
                len(structure[2]))

            # String format structure
            infostr = "All connected instances in the network:\n"
            infostr += "\n" + structure[0]
            infostr += self.formatNetworklist(tuple(structure))

            self.sendMsgTo(clientid, infostr)

        def restartserver(clientid, args):
            port = self.getSockData('Serversock')
            port = port[0].getsockname()[1]
            for servername in args:
                server_id = self.getIDof(username=servername)
                if server_id is not None:
                    if self.conns[server_id]['isserver']:
                        cl_data = self.conns[clientid]['data']
                        if f"restart_{servername}_ack" in cl_data \
                        and cl_data[f'restart_{servername}_ack'] >= \
                        time() - 30:
                            self.sendMsgTo(
                                clientid,
                                f"Restarting server '{servername}'")
                            self.sendCommandTo(
                                self.conns[server_id]['socks'][port],
                                "restart")
                        elif f"restart_{servername}_ack" in cl_data:
                            self.sendMsgTo(clientid,
                                               "Restart confirmation expired")
                        self.conns[clientid]['data'][
                            f"restart_{servername}_ack"] = time()
                        self.sendMsgTo(
                            clientid,
                            f"Send 's.restartserver({servername})' again to "
                            + "confirm the restart of that server")
                    else:
                        self.sendMsgTo(
                            clientid,
                            f"Connection '{servername}' is no server")
                else:
                    self.sendMsgTo(
                        clientid,
                        f"No connection '{servername}' existing")

        def shutdownserver(clientid, args):
            for servername in args:
                server_id = self.getIDof(username=servername)
                if server_id is not None:
                    if self.conns[server_id]['isserver']:
                        cl_data = self.conns[clientid]['data']
                        if f"shutdown_{servername}_ack" in cl_data \
                        and cl_data[f'shutdown_{servername}_ack'] >= \
                        time()-30:
                            self.sendMsgTo(
                                clientid,
                                f"Shutting server '{servername}' down")
                            self.sendCommandTo(
                                self.mainSocketof(server_id), "shutdown")
                            return
                        elif f'shutdown_{servername}_ack' in cl_data:
                            self.sendMsgTo(clientid,
                                               "Shutdown confirmation expired")
                        self.conns[clientid]['data'][
                            f'shutdown_{servername}_ack'] = time()
                        self.sendMsgTo(
                            clientid,
                            f"Send 's.shutdownserver({servername})' again to "
                            + "confirm the shutdown of that server")
                    else:
                        self.sendMsgTo(
                            clientid,
                            f"Connection '{servername}' is no server")
                else:
                    self.sendMsgTo(
                        clientid,
                        f"No connection '{servername}' existing")

        def shutdownnetwork(clientid):
            cl_data = self.conns[clientid]['data']
            if 'shutdown_net_ack' in cl_data \
            and cl_data['shutdown_net_ack'] >= time() - 30:
                port = self.getSockData('Serversock')
                port = port[0].getsockname()[1]
                for connid in self.conns:
                    self.sendMsgTo(connid, "Network is shutting down")
                    conn = self.conns[connid]
                    if conn['isserver']:
                        self.sendCommandTo(conn['socks'][port],
                                           'shutdownnetwork')
                    else:
                        self.sendCommandTo(conn['socks'][port], 'disconnect')
                self.shutdownServer()
                return
            elif 'shutdown_net_ack' in cl_data:
                self.sendMsgTo(clientid, "Shutdown confirmation expired")
            self.conns[clientid]['data']['shutdown_net_ack'] = time()
            self.sendMsgTo(
                clientid,
                "Send 's.shutdownnetwork()' again to confirm the shutdown "
                + "of the whole network")

        # User management
        self.newServerCommand(
            's.listnetwork', "Shows all connections and their sub-connections",
            lambda id, args: listnetwork(id),
            category='statistic')

        # Network management
        self.newServerCommand(
            's.restartserver', "Restarts a connected server",
            lambda id, args: restartserver(id, args),
            repeatable_arg='serverusername',
            needed_permission='admin',
            category='network management')
        self.newServerCommand(
            's.shutdownserver', "Shuts a connected server down",
            lambda id, args: shutdownserver(id, args),
            repeatable_arg='serverusername',
            needed_permission='admin',
            category='network management')
        self.newServerCommand(
            's.shutdownnetwork', "Shuts every server in the network down",
            lambda id, args: Thread(
                target=shutdownnetwork, args=(id,), name='Shutdown network'
                ).start(),
            needed_permission='admin',
            category='network management')

    def startServer(self):
        """Binds the sockets and starts all server services.

        ...

        ---
        See Also
        --------
        network.Server.startServer : Start a server and its services
        """

        if self.se_running:
            self.statusInfo("Mainserver is already running")
        Server.startServer(self, self.preferredport, self.preferreddataport,
                           True, True)
        self.statusInfo("Mainserver operational")

    def formatNetworklist(self, network: tuple[str, list[Any], list[str]],
                          last: bool=True, prefix: str="") -> str:
        """Recursive string formatting for a list with connections.

        ...

        Uses a network structure list with all clients and subserver is
        the network and formats it to a readable string list.

        ---
        Parameters
        ----------
        network : tuple[list[str], list[str]]
            List with all clients and subserver in the network
        last : bool
            Indicator that this is the last entry in the recursive depth
        prefix : str
            Prefix for a new line

        ---
        Returns
        -------
        str : Formatted network structure

        ---
        Notes
        -----
        - The *network structure list* can be gained with a
        'LISTNETWORK' data request.
        - This is used by the 's.listnetwork()' *servercommand*.

        ---
        Examples
        --------
        >>> ms.formatNetworklist(
        ...    ['Mainserver(192.168.178.140)  0 servers  1 clients',
        ...     [], ['con(192.168.178.140)']])
        Mainserver(192.168.178.140)  0 servers  1 clients
        |----> con(192.168.178.140)
        >>> ms.formatNetworklist(
        ...    ['Mainserver(192.168.178.140)',
        ...     [['Testserver(192.168.178.140)',
        ...      [], ['unnamed_92951(192.168.178.140)']]],
        ...     ['con(192.168.178.140)']])
        Mainserver(192.168.178.140)
        |----> con(192.168.178.140)
        |
        |---Testserver(192.168.178.140)
            |----> unnamed_92951(192.168.178.140)
        """

        if last and len(prefix) >= 3:
            prefix = f"{prefix[:-3]}   "
        formatted="".join(f"\n{prefix} ├──> {client}" for client in network[2])
        if len(network[2]) > 0 and len(network[1]) > 0:
            formatted += f"\n{prefix} |"
        for server in network[1]:
            formatted += f"\n{prefix} ├─ {server[0]}"
            formatted += self.formatNetworklist(
                server,
                server == network[1][-1],
                f"{prefix} | ")
        if not network[1]:
            formatted += f"\n{prefix}"
        return formatted
