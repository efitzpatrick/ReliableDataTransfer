import binascii

import random
from scapy.all import Packet
from scapy.all import IntField
from socket import socket, AF_INET, SOCK_DGRAM
import time

START = 0
END = 1
DATA = 2
ACK = 3
END_ACK = 4


def corrupt_data(data):
    raw = list(data)
    for i in range(0, random.randint(1, 3)):
        pos = random.randint(0, len(raw) - 1)
        raw[pos] = random.randint(0, 255)
    return bytes(raw)


class UnreliableSocket(object):
    def __init__(self):
        self.sock = socket(AF_INET, SOCK_DGRAM)
        self.sock.setblocking(False)
        self.loss_rate = 0.1
        self.corruption_rate = 0.3
        self.delay_rate = 0.1
        self.delay_time = 0.5

    def bind(self, address):
        self.sock.bind(address)

    def recvfrom(self, bufsize):
        data, addr = self.sock.recvfrom(bufsize)
        pkt_header = PacketHeader(data[:16])
        if random.random() < self.delay_rate:
            time.sleep(self.delay_time)
            return data, addr
        if random.random() < self.loss_rate:
            if pkt_header.type != END and pkt_header.type != END_ACK:
                return self.recvfrom(bufsize)
        if random.random() < self.corruption_rate:
            if pkt_header.type != END and pkt_header.type != END_ACK:
                return corrupt_data(data), addr
        return data, addr

    def sendto(self, data, addr):
        return self.sock.sendto(data, addr)

    def close(self):
        self.sock.close()


class PacketHeader(Packet):
    name = "PacketHeader"
    fields_desc = [
        IntField("type", 0),
        IntField("seq_num", 0),
        IntField("length", 0),
        IntField("checksum", 0),
    ]


def compute_checksum(pkt):
    return binascii.crc32(bytes(pkt)) & 0xffffffff


def verify_packet(pkt_header, msg):
    pkt_checksum = pkt_header.checksum
    pkt_header.checksum = 0
    computed_checksum = compute_checksum(pkt_header / msg)
    return True if pkt_checksum == computed_checksum else False
