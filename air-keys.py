from time import sleep
from socket import socket, AF_INET, SOCK_DGRAM, SOCK_STREAM, SOL_SOCKET, SO_BROADCAST, gethostbyname, gethostname
import select
import secrets
import keyboard
import pynput

MAGIC = b'0xgr33n134f'
BROAD_PORT = 7777
PACK_SIZE = 16


def strip_magic(data: bytes, magic=MAGIC) -> bytes:
    return data[len(magic):]


def pad_data(data: bytes, size=PACK_SIZE) -> bytes:
    return data + b" " * (size - len(data))


def source_client():
    # Create the UDP broadcast socket
    broad_sock = socket(AF_INET, SOCK_DGRAM)
    broad_sock.bind(('', 0))
    broad_sock.setsockopt(SOL_SOCKET, SO_BROADCAST, 1)

    # Create the TCP socket for communication
    s_sock = socket(AF_INET, SOCK_STREAM)
    s_sock.listen(1)
    s_sock_port = s_sock.getsockname()[1]

    print("Broadcasting myself")

    com_sock = None

    while True:
        print("...")
        broad_sock.sendto(MAGIC + str(s_sock_port).encode(), ('<broadcast>', BROAD_PORT))
        # Check if the destination client sent a response
        ready = select.select([s_sock], [], [], 2)
        if s_sock in ready[0]:
            conn, addr = s_sock.accept()
            print("Received connection from:", addr)
            com_sock = conn
            break

    broad_sock.close()
    s_sock.close()
    
    if com_sock is None:
        print("ERROR: Destination socket not set")
        exit()
    
    while True:
        with pynput.keyboard.Events() as events:
            event = events.get()

            # Parse type of key event, appending P for press, R for release, and E for exit
            if event is None:
                continue
            if event.key == pynput.keyboard.Key.backspace:
                print("Exiting")
                com_sock.send(pad_data(b"E"))
                break
            data = b""
            if isinstance(event, pynput.keyboard.Events.Press):
                data += b"P"
            elif isinstance(event, pynput.keyboard.Events.Release):
                data += b"R"
            else:
                continue

            # Clean up keycode
            keycode = str(event.key).strip("'")
            if keycode.startswith("Key."):
                keycode = keycode[4:]
            if keycode.endswith("_r"):
                keycode = keycode[:-2]
            data += keycode.encode()

            # Pad data to PACK_SIZE
            data = pad_data(data)

            # Send event to destination client
            print("Sending:", data.decode())
            com_sock.send(data)

    com_sock.close()
        

def destination_client():
    # Create a UDP socket for receiving broadcasts
    broad_sock = socket(AF_INET, SOCK_DGRAM)
    broad_sock.bind(('', BROAD_PORT))
    broad_sock.setsockopt(SOL_SOCKET, SO_BROADCAST, 1)
    
    # Create a TCP socket for communication
    com_sock = socket(AF_INET, SOCK_STREAM)

    print("Waiting for source client broadcast")
    while True:
        data, addr = broad_sock.recvfrom(1024)
        if data.startswith(MAGIC):
            com_port = int(strip_magic(data).decode())
            print("Received client broadcast")
            print("Connecting to:", addr)
            addr = (addr[0], com_port)
            com_sock.connect(addr)
            break
    
    broad_sock.close()

    buf = b""
    
    # Receive messages from the source client
    while True:
        data = com_sock.recv(PACK_SIZE)
        if (len(data) == 0):
            print("Client disconnected")
            break
        buf += data
        while len(buf) >= PACK_SIZE:
            data = buf[:PACK_SIZE]
            buf = buf[PACK_SIZE:]
            press = False
            release = False
            if data.startswith(b"E"):
                print("Client disconnected")
                return
            elif data.startswith(b"P"):
                press = True
            elif data.startswith(b"R"):
                release = True
            else:
                print("Received somthing weird:", data.decode())
                continue
            keycode = data[1:].decode().strip()
            # Send key to keyboard
            print("Sending", keycode, "to keyboard")
            try:
                keyboard.send(keycode, do_press=press, do_release=release)
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
        while True:
            destination_client()
    else:
        exit()
