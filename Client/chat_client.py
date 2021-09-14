import socket
import errno
import pickle
from threading import Thread

HEADER_LENGTH = 10
client_socket = None


# Connects to the server
def connect(ip, port, *args, new_account = False, error_callback = print):

    global client_socket

    # Create a socket
    # socket.AF_INET - address family, IPv4, some otehr possible are AF_INET6, AF_BLUETOOTH, AF_UNIX
    # socket.SOCK_STREAM - TCP, conection-based, socket.SOCK_DGRAM - UDP, connectionless, datagrams, socket.SOCK_RAW - raw IP packets
    client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    try:
        # Connect to a given ip and port
        client_socket.connect((ip, port))
    except Exception as e:
        # Connection error
        error_callback('The server is not running')
        return

    # Prepare username and header and send them
    # We need to encode username to bytes, then count number of bytes and prepare header of fixed size, that we encode to bytes as well
    creds = ' '.join((*args,new_account))
    creds = creds.encode('utf-8')
    creds_header = f"{len(creds):<{HEADER_LENGTH}}".encode('utf-8')
    client_socket.send(creds_header + creds)
    try:
        #Check if we have access to the server
        access = client_socket.recv(HEADER_LENGTH).strip()
        if access.decode('utf-8') == '1':
            return False
        else:
            return True
    except:
        #Something went wrong
        error_callback('Connection closed by the server')

def recieve_message(error_callback, python_object=False):
    #Recieve the username
    username_header = client_socket.recv(HEADER_LENGTH)
    if not len(username_header):
        error_callback('Connection closed by the server')
    #Get the username from the username length
    username_length = int(username_header.decode('utf-8').strip())
    username = client_socket.recv(username_length).decode('utf-8')
    #Do the same for message
    message_header = client_socket.recv(HEADER_LENGTH)
    message_length = int(message_header.decode('utf-8').strip())
    message = client_socket.recv(message_length)
    #Return the message to the user
    return message.decode('utf-8') if not python_object else pickle.loads(message)

# Sends a message to the server
def send(to_username,message):
    # Encode message to bytes, prepare header and convert to bytes, like for username above, then send
    message = to_username.encode('utf-8') + ' '.encode('utf-8') + message.encode('utf-8')
    message_header = f"{len(message):<{HEADER_LENGTH}}".encode('utf-8')
    client_socket.send(message_header + message)

def send_server_request(message, error_callback,er=True, python_object = False):
    #Do the same but send a server request
    message = message.encode('utf-8')
    message_header = f"{len(message):<{HEADER_LENGTH}}".encode('utf-8')
    client_socket.send(message_header + message)
    if er:
        received_message = recieve_message(error_callback, python_object)
        return received_message

# Starts listening function in a thread
# incoming_message_callback - callback to be called when new message arrives
# error_callback - callback to be called on error
def start_listening(incoming_message_callback, error_callback):
    Thread(target=listen, args=(incoming_message_callback,error_callback),daemon=True).start()
    print('Listening for incoming messages')

# Listens for incomming messages
def listen(incoming_message_callback,error_callback):
    while True:
        try:
            # Receive our "header" containing username length, it's size is defined and constant
            username_header = client_socket.recv(HEADER_LENGTH)

            # If we received no data, server gracefully closed a connection, for example using socket.close() or socket.shutdown(socket.SHUT_RDWR)
            if not len(username_header):
                return

            # Convert header to int value
            username_length = int(username_header.decode('utf-8').strip())

            # Receive and decode username
            username = client_socket.recv(username_length).decode('utf-8')

            # Now do the same for message (as we received username, we received whole message, there's no need to check if it has any length)
            message_header = client_socket.recv(HEADER_LENGTH)
            message_length = int(message_header.decode('utf-8').strip())
            message = client_socket.recv(message_length).decode('utf-8')

            # Print message
            incoming_message_callback(username, message)
        
        except Exception as e:
            # Any other exception - something happened, exit
            print(e)
            print('Connection aborted')
            break
        
def close():
    #Close connection to server
    client_socket.shutdown(socket.SHUT_RD)
    client_socket.close()
    print('Connection to server has been closed')
