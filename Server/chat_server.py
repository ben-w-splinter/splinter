import socket
import select
import pickle
from threading import Thread
from collections import defaultdict
import server_db

HEADER_LENGTH = 10

IP = '127.0.0.1'
PORT = 2020

# Create a socket
# socket.AF_INET - address family, IPv4, some otehr possible are AF_INET6, AF_BLUETOOTH, AF_UNIX
# socket.SOCK_STREAM - TCP, conection-based, socket.SOCK_DGRAM - UDP, connectionless, datagrams, socket.SOCK_RAW - raw IP packets
server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

# SO_ - socket option
# SOL_ - socket option level
# Sets REUSEADDR (as a socket option) to 1 on socket
server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

# Bind, so server informs operating system that it's going to use given IP and port
# For a server using 0.0.0.0 means to listen on all available interfaces, useful to connect locally to 127.0.0.1 and remotely to LAN interface IP
server_socket.bind((IP, PORT))

# This makes server listen to new connections
server_socket.listen()

# List of sockets for select.select()
sockets_list = [server_socket]

# List of connected clients - username as key, socket as data
clients = {}

print(f'Listening for connections')

#Message queue class to hold incoming messages
class MessageQueue:
    def __init__(self):
        #Create dictionary to store messages
        self.messages = defaultdict(list)

    def add_message(self,origin,destination,message):
        #adds a message to the queue using the destination as the key
        self.messages[destination].append([origin,message])
    
    def find_user_messages(self,username):
        #Finds the messages for a given username and deletes them from the queue
        try:
            return_msg = self.messages[username]
            del self.messages[username]
            return return_msg
        except KeyError:
            return 0

#Innits the queue
message_queue = MessageQueue()

#Forwards message to user
def forward_message(from_username,to_username,message):
    try: 
        #Check if the client is connected
        address = {'header': f'{len(to_username):<{HEADER_LENGTH}}'.encode('utf-8'), 'data': to_username.encode('utf-8')}
        destination = [key  for (key, value) in clients.items() if value == address][0]
    except IndexError:
        #If not store the message
        print('Storing message')
        message_queue.add_message(from_username,to_username,message)

    else:
        #Encode and forward the message
        message_header = f'{len(message):<{HEADER_LENGTH}}'.encode('utf-8')
        message = message.encode('utf-8')
        username_header = f'{len(from_username):<{HEADER_LENGTH}}'.encode('utf-8')
        username = from_username.encode('utf-8')
        print('Forwarding message')
        destination.send(username_header + username + message_header + message)

def handle_login(creds,new_account):
    #Check if the user is new or they are trying to log in
    func = server_db.create_user if new_account == 'True' else server_db.login_check
    return func(*creds)

def handle_message(message,from_username):
    """Returns True if a normal message was recieved, else handles the request"""
    if not message or message[0] != '$':
        return [True,message]
    request = message[1:].split() #Removes the dollar from the message and splits
    
    #Finds the server request
    if request[0] == '1':
        print('Friend request recieved')
        #Check if the chosen user exists
        if not server_db.user_exists(request[1]):
            return [False,'1']
        #Check if they are already friends
        elif not server_db.contact_check(request[1],from_username):
            return [False, '2']
        else:
            #All checks have passed, forward the message onto the user
            s_msg,s_usr = message.split()
            print(f's_usr = {s_usr}')
            forward_message('$server fw',s_usr,f'{from_username} {server_db.get_name(from_username)}')
            return [False,'3']

    elif request[0] == '2':
        print('Request accepted')
        server_db.add_contact(request[1],from_username)
        return

    elif request[0] == '3':
        print('Message request recieved')
        return [False,pickle.dumps(message_queue.find_user_messages(request[1]))]
    
    elif request[0] == '4':
        print('Fetch contacts request recieved')
        return [False, pickle.dumps(server_db.get_contacts(request[1]))]
    
    else:
        #Invalid request sent
        return [False,'404']

# Handles message receiving
def receive_message(client_socket):

    try:

        # Receive our "header" containing message length, it's size is defined and constant
        message_header = client_socket.recv(HEADER_LENGTH)

        # If we received no data, client gracefully closed a connection, for example using socket.close() or socket.shutdown(socket.SHUT_RDWR)
        if not len(message_header):
            return False

        # Convert header to int value
        message_length = int(message_header.decode('utf-8').strip())

        # Return an object of message header and message data
        return {'header': message_header, 'data': client_socket.recv(message_length)}

    except:

        # If we are here, client closed connection violently, for example by pressing ctrl+c on his script
        # or just lost his connection
        # socket.close() also invokes socket.shutdown(socket.SHUT_RDWR) what sends information about closing the socket (shutdown read/write)
        # and that's also a cause when we receive an empty message
        return False

def main(notified_socket):
    if notified_socket == server_socket:
        # Accept new connection
        # That gives us new socket - client socket, connected to this given client only, it's unique for that client
        # The other returned object is ip/port set
        client_socket, client_address = server_socket.accept()

        # Client should send his name right away, receive it
        user = receive_message(client_socket)

        # If False - client disconnected before he sent his name
        if user is False:
            return

        #Obtain the user credentials
        creds = user['data'].decode('utf-8').split(' ')
        creds, new_account = creds[:-1],creds[-1]
        #Check if the user can make an account
        acess = handle_login(creds,new_account)
        if acess:
            print('Acess granted')

            # Add accepted socket to select.select() list
            sockets_list.append(client_socket)

            # Also save username and username header
            clients[client_socket] = {'header': f"{len(creds[0]):<{HEADER_LENGTH}}".encode('utf-8'), 'data': creds[0].encode('utf-8')}

            print('Accepted new connection from {}:{}, username: {}'.format(*client_address, user['data'].decode('utf-8')))
            print('Sending reply')
            client_socket.send('2'.encode('utf-8'))
        else:
            print('Acess denied, sending reply')
            client_socket.send('1'.encode('utf-8'))



    # Else existing socket is sending a message
    else:

        # Receive message
        message = receive_message(notified_socket)

        # If False, client disconnected, cleanup
        if message is False:
            print("Closed connection from: {}".format(clients[notified_socket]['data']))

            # Remove from list for socket.socket()
            sockets_list.remove(notified_socket)

            # Remove from our list of users
            del clients[notified_socket]

            return

        # Get user by notified socket, so we will know who sent the message
        user = clients[notified_socket]

        #Decode the message
        result = handle_message(message['data'].decode('utf-8'),user['data'].decode('utf-8'))

        if result == None: #Nothing needs to be sent
            return
        if not result[0]: #Checks if result was request
            print('Sending request')
            #Send the reply back to the user
            reply_user_data = '$server'.encode('utf-8')
            reply_user_header = f'{len(reply_user_data):<{HEADER_LENGTH}}'.encode('utf-8')
            reply_message_data = result[1]
            try:
                reply_message_data = reply_message_data.encode('utf-8')
            except AttributeError:
                pass
            reply_message_header = f'{len(reply_message_data):<{HEADER_LENGTH}}'.encode('utf-8')
            notified_socket.send(reply_user_header + reply_user_data + reply_message_header + reply_message_data)

        else:
            #Normal message recieved, forward on to user
            print(f'Message received from {user["data"].decode("utf-8")}: {message["data"].decode("utf-8")}')
            content =  message['data'].decode('utf-8').split(' ')
            username, message = content[0], ' '.join(content[1:])
            forward_message(user['data'].decode('utf-8'),username,message)

while True:
    try:

        # Calls Unix select() system call or Windows select() WinSock call with three parameters:
        #   - rlist - sockets to be monitored for incoming data
        #   - wlist - sockets for data to be send to (checks if for example buffers are not full and socket is ready to send some data)
        #   - xlist - sockets to be monitored for exceptions (we want to monitor all sockets for errors, so we can use rlist)
        # Returns lists:
        #   - reading - sockets we received some data on (that way we don't have to check sockets manually)
        #   - writing - sockets ready for data to be send thru them
        #   - errors  - sockets with some exceptions
        # This is a blocking call, code execution will "wait" here and "get" notified in case any action should be taken
        read_sockets, _, exception_sockets = select.select(sockets_list, [], sockets_list)


        # Iterate over notified sockets
        for notified_socket in read_sockets:
            main(notified_socket)

        #Closes dead connection
        for notified_socket in exception_sockets:
            print("Closed connection from: {}".format(clients[notified_socket]['data'].decode('utf-8')))
            sockets_list.remove(notified_socket)
            del clients[notified_socket]
    
    except KeyboardInterrupt:
        print('Server closed, you may now exit the terminal')
        break
