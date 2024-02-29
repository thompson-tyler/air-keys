from socket import (
    socket,
    AF_INET,
    SOCK_DGRAM,
    SOCK_STREAM,
    SOL_SOCKET,
    SO_BROADCAST,
)
import select
import keyboard
import pynput
import secrets
import sys
import argparse

MAGIC = b"gr33n134f"
BROAD_PORT = 7777
PACK_SIZE = 16
CONFIRM_CODE_LEN = 4


def strip_magic(data: bytes, magic=MAGIC) -> bytes:
    return data[len(magic) :]


def pad_data(data: bytes, size=PACK_SIZE) -> bytes:
    return data + b" " * (size - len(data))


def clean_keycode(keycode: str) -> str:
    keycode = keycode.strip("'")
    if keycode.startswith("Key."):
        keycode = keycode[4:]
    if keycode.endswith("_r"):
        keycode = keycode[:-2]
    return keycode


def source_client():
    # Create a UDP socket for receiving broadcasts
    broad_sock = socket(AF_INET, SOCK_DGRAM)
    broad_sock.bind(("", BROAD_PORT))
    broad_sock.setsockopt(SOL_SOCKET, SO_BROADCAST, 1)

    # Create a TCP socket for communication
    com_sock = socket(AF_INET, SOCK_STREAM)

    while True:
        print("Waiting for destination broadcast")
        data, addr = broad_sock.recvfrom(1024)

        # Check if broadcast is from this program
        if not data.startswith(MAGIC):
            continue

        # Parse nonce and TCP port
        data = strip_magic(data).decode()
        nonce = data[:CONFIRM_CODE_LEN]
        try:
            com_port = int(data[CONFIRM_CODE_LEN:])
        except:
            # Got a non-numeric port
            continue

        # Confirm that the destination client is the one we want
        print("Received destination broadcast")
        print("Does this code match the one on the destination client?")
        print(nonce)
        if input("y/n: ").lower() != "y":
            continue
        addr = (addr[0], com_port)
        com_sock.connect(addr)
        print("Connected to destination client")
        break

    broad_sock.close()

    if com_sock is None:
        print("ERROR: Destination socket not set")
        exit()

    # Setup key state table
    key_state = {}

    def send_key(key: str, event: str):
        if key in key_state and key_state[key] == event:
            return
        key_state[key] = event

        data = event.encode()
        data += clean_keycode(key).encode()

        # Pad data to PACK_SIZE
        data = pad_data(data)[:PACK_SIZE]

        # Send event to destination client
        print("Sending:", data.decode())
        com_sock.send(data)

    with pynput.keyboard.Listener(
        on_press=(lambda key: send_key(str(key), "P")),
        on_release=(lambda key: send_key(str(key), "R")),
    ) as listener:
        listener.join()


def destination_client():
    # Create the UDP broadcast socket
    broad_sock = socket(AF_INET, SOCK_DGRAM)
    broad_sock.bind(("", 0))
    broad_sock.setsockopt(SOL_SOCKET, SO_BROADCAST, 1)

    # Create the TCP socket for communication
    s_sock = socket(AF_INET, SOCK_STREAM)
    s_sock.bind(("", 0))
    s_sock.listen(1)
    s_sock_port = s_sock.getsockname()[1]

    com_sock = None
    nonce = secrets.token_urlsafe(CONFIRM_CODE_LEN)[:CONFIRM_CODE_LEN].upper()

    while True:
        print("Broadcasting myself:", nonce)
        # hack to flush stdout. Done because some machines don't flush stdout and it appears
        # that the program is hanging
        sys.stdout.flush()
        broad_sock.sendto(
            MAGIC + nonce.encode() + str(s_sock_port).encode(),
            ("<broadcast>", BROAD_PORT),
        )
        # Check if a source client wants to connect
        ready = select.select([s_sock], [], [], 2)
        if s_sock in ready[0]:
            conn, addr = s_sock.accept()
            print("Received connection from:", addr)
            com_sock = conn
            break

    broad_sock.close()
    s_sock.close()

    buf = b""
    # Receive messages from the source client
    while True:
        data = com_sock.recv(PACK_SIZE)
        if len(data) == 0:
            print("Client disconnected")
            break
        buf += data
        while len(buf) >= PACK_SIZE:
            data = buf[:PACK_SIZE]
            buf = buf[PACK_SIZE:]
            if data.startswith(b"E"):
                print("Client disconnected")
                com_sock.close()
                return
            elif data.startswith(b"P"):
                press = True
            elif data.startswith(b"R"):
                press = False
            else:
                print("Received somthing weird:", data.decode())
                continue
            keycode = data[1:].decode().strip().lower()
            # Send key to keyboard
            try:
                if press:
                    keyboard.press(keycode)
                else:
                    keyboard.release(keycode)
                # keyboard.send(keycode, do_press=press, do_release=release)
            except:
                print("Failed to send key!")


if __name__ == "__main__":
    # See if the user passed any arguments
    parser = argparse.ArgumentParser(description="AirKeys")
    group = parser.add_mutually_exclusive_group()
    group.add_argument(
        "-s", "--source", action="store_true", help="Start as source client"
    )
    group.add_argument(
        "-d",
        "--destination",
        action="store_true",
        help="Start as destination client",
    )
    args = parser.parse_args()

    # If the user passed an argument, start the appropriate client
    if args.source:
        source_client()
        exit()
    elif args.destination:
        while True:
            destination_client()

    # The client didn't pass any arguments! Ask the user what they want to do
    print("1) Source client")
    print("2) Destination client")
    print("3) Exit")
    try:
        choice = int(input("Enter your choice: "))
    except:
        exit()
    if choice == 1:
        source_client()
    elif choice == 2:
        while True:
            destination_client()
    else:
        exit()
