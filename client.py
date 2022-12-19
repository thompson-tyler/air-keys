from time import sleep
from socket import socket, AF_INET, SOCK_DGRAM, SOL_SOCKET, SO_BROADCAST, gethostbyname, gethostname
import select
import secrets
import keyboard
import pynput

MAGIC = b'0xgr33n134f'
PORT = 7777

def strip_magic(data: bytes, magic=MAGIC) -> bytes:
    return data[len(magic):]

def source_client():
    # Create a socket object
    s = socket(AF_INET, SOCK_DGRAM)
    s.bind(('', 0))
    s.setsockopt(SOL_SOCKET, SO_BROADCAST, 1)
    my_ip = gethostbyname(gethostname())

    dest_addr = None
    dest_nonce = None
    print("Broadcasting myself")

    while True:
        print("...")
        s.sendto(MAGIC, ('<broadcast>', PORT))
        # Check if the destination client sent a response
        ready = select.select([s], [], [], 2)
        if s in ready[0]:
            data, addr = s.recvfrom(1024)
            if data.startswith(MAGIC):
                print("Received response, starting communication")
                dest_addr = addr
                dest_nonce = strip_magic(data)
                break
            else:
                print("Received unknown data:", data.decode())
    
    if dest_addr is None or dest_nonce is None:
        print("ERROR: Destination not set")
        exit()
    
    while True:
        with pynput.keyboard.Events() as events:
            event = events.get()
            if event is None:
                continue
            if event.key == pynput.keyboard.Key.esc:
                s.sendto(dest_nonce + b"E", dest_addr)
                break
            data = b""
            if isinstance(event, pynput.keyboard.Events.Press):
                data += b"P"
            elif isinstance(event, pynput.keyboard.Events.Release):
                data += b"R"
            else:
                continue
            data += str(event.key).strip("'").encode()
            print("Sending:", data.decode())
            # Send event to destination client
            s.sendto(dest_nonce + data, dest_addr)

    print("Exiting")
        

def destination_client():
    # Create a socket object
    s = socket(AF_INET, SOCK_DGRAM)
    s.bind(('', PORT))
    s.setsockopt(SOL_SOCKET, SO_BROADCAST, 1)
    # Generate random nonce
    nonce = secrets.token_bytes(16)

    print("Waiting for source client broadcast")
    while True:
        data, addr = s.recvfrom(1024)
        if data.startswith(MAGIC):
            print("Received client broadcast")
            print("Sending nonce to:", addr)
            s.sendto(MAGIC + nonce, addr)
            break
    
    # Receive messages from the source client
    while True:
        data, addr = s.recvfrom(1024)
        if data.startswith(nonce):
            data = strip_magic(data, nonce)
            press = False
            release = False
            if data.startswith(b"E"):
                print("Client exited")
                break
            elif data.startswith(b"P"):
                print("Pressed:", data[1:].decode())
                press = True
            elif data.startswith(b"R"):
                print("Released:", data[1:].decode())
                release = True
            else:
                print("Received somthing weird:", data.decode())
                continue

            keycode = data[1:].decode()
            # Clean up keycode
            if keycode.startswith("Key."):
                keycode = keycode[4:]
            if keycode.endswith("_r"):
                keycode = keycode[:-2]
            
            # Send key to keyboard
            try:
                keyboard.send(data[1:].decode(), do_press=press, do_release=release)
            except:
                print("Failed to send key")



if __name__ == '__main__':
    print("1) Source client")
    print("2) Destination client")
    print("3) Exit")
    choice = int(input("Enter your choice: "))
    if choice == 1:
        source_client()
    elif choice == 2:
        destination_client()
    else:
        exit()
