import sys
from rdt import RDTSocket

from util import *


def main():
    """Parse command-line argument and call sender function """
    if len(sys.argv) != 4:
        sys.exit("Usage: python sender.py [Receiver IP] [Receiver Port] [Window Size]")
    receiver_ip = sys.argv[1]
    receiver_port = int(sys.argv[2])
    window_size = int(sys.argv[3])
    s_sock = RDTSocket(window_size, receiver_port)
    s_sock.connect((receiver_ip, receiver_port))
    with open('alice.txt', 'r') as f:
        data = f.read()
        s_sock.send(data.encode())
        s_sock.close()


if __name__ == "__main__":
    main()
