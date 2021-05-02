import math
import sys
from socket import *
import numpy
from queue import PriorityQueue

import util
from util import *
import time
import random

PACKET_SIZE = 50  # 1472  # 1500-8(udp header)-20(IP header) = 1472
PAYLOAD_SIZE = 1456  # 1472(PACKET_SIZE)-16(Header) = 1456
ret_time = .5  # timeout value


def unpack(packet):
    pkt_header = PacketHeader(packet[:16])
    pkt_msg = packet[16:16 + pkt_header.length]
    valid_packet = verify_packet(pkt_header, pkt_msg)
    if valid_packet:
        return pkt_header, pkt_msg
    else:
        print("corrupt packet")
        raise CorruptPacket


def split_bytes(_bytes):
    chunk_size = PAYLOAD_SIZE
    number_of_chunks = len(_bytes) / PACKET_SIZE
    number_of_chunks = math.ceil(number_of_chunks)
    chunks, chunk_size = len(_bytes), math.ceil(len(_bytes) / number_of_chunks)
    if chunks < 1:
        chunks = 1
        chunk_size = len(_bytes)
    data = [_bytes[i:i + chunk_size] for i in range(0, chunks, chunk_size)]
    return data


class RDTSocket(UnreliableSocket):
    """
    You need to implement the following functions to provide reliability over UnreliableSocket
    """

    def __init__(self, window_size, port, ip="127.0.0.1"):
        super(RDTSocket, self).__init__()
        self.window = {}  # keeps mapping of <seq_num, message> pairs
        self.window_size = window_size
        self._send_to = (ip, port)  # specifies the address of the socket on the other side
        self.send_base = 0  # points to the oldest unacked packet
        self.recv_base = 0  # points to the next expected packet
        """
        Add any other necesesary initial arguments
        """

    def accept(self) -> list:
        """
        Invoked by reciever
        Accept a connection. The socket must be bound to an address and listening for
        connections. The return value is the address of the socket on the other end of the connection (tuple of IP and port number).

        This function should be a blocking function.
        """
        while True:
            try:
                data, addr = self.recvfrom(PACKET_SIZE)
                self._send_to = addr
                if data and addr:
                    header, msg = unpack(data)
                    self.send_base = header.seq_num
                    self.send_packet(util.ACK, "", header.seq_num)
                    print("acked start")
                    return addr
            except BlockingIOError:
                pass
            except CorruptPacket:
                pass

    def connect(self, address):
        """
        Invoked by sender
        Connect to a remote socket at address.
        Corresponds to the process of establishing a connection on the client side.
        """
        # TODO Set seq_num equal to something random
        # TODO needs to loop until ack is recieved
        self.send_base = 0
        self._send_to = address
        while True:
            self.send_packet(util.START, "", 0)
            print("sending packet")
            try:
                self.recvfrom(PACKET_SIZE)
                print("recieved ack")
                return
            except BlockingIOError:
                pass
            except CorruptPacket:
                pass

    def recv(self, bufsize):
        """
        Invoked by reciever
        Reassemble chunks and pass message back into the application process
        Use verify_packet() to check integrity
        -------
        Receive data from the socket. The return value is the received data.
        The maximum amount of data to be received at once is specified by bufsize.
        """
        data = None
        assert self._send_to, "Connection not established yet."
        data = b''
        buffer = Buffer()
        while True:
            try:
                packet, _ = self.recvfrom(bufsize)
                header, msg = unpack(packet)
                if header.type == util.DATA:
                    # If in sequence
                    print("recieved ", header.seq_num)
                    if header.seq_num == self.recv_base:
                        data += msg
                        self.recv_base += 1

                        while buffer.peek() == self.recv_base:
                            msg = buffer.get()[1]
                            data += msg
                            self.recv_base += 1

                        self.send_ack(util.ACK)

                    elif header.seq_num > self.recv_base:
                        buffer.put((header.seq_num, msg))
                        self.send_ack(util.ACK)

                    else:
                        self.send_ack(util.ACK)
                elif header.type == util.END:
                    self.send_ack(util.END_ACK)
                    print("send end ack")
                    return data.decode()
            except BlockingIOError:
                pass
            except CorruptPacket:
                pass

    def send(self, _bytes):
        """
        Invoked by sender
        Split data into appropriate chunk size
        Send data to the socket. _bytes contains the bytearray of the data.
        The socket must be connected to a remote socket, seq_num.e. self._send_to must not be none.
        """
        self.send_base = self.send_base
        assert self._send_to, "Connection not established yet. Use sendto instead."
        chunks = split_bytes(_bytes)
        # Send all messages
        self.send_all_chunks(chunks)
        # Send and wait for end
        self.close()

    def send_all_chunks(self, chunks):
        start_time = time.time()
        # Keeps track of the sent messages
        sent = []
        end_window = self.send_base + self.window_size + 1
        if end_window > len(chunks): end_window = len(chunks)
        for send_num in range(self.send_base, end_window):
            self.send_packet(util.DATA, chunks[send_num], send_num)
            sent.append(send_num)
            print(send_num)
        while self.recv_base < len(chunks):
            # TODO implement random starting value for seq_num
            try:
                recv_ack, _ = self.recvfrom(PACKET_SIZE)
                if recv_ack:
                    header, msg = unpack(recv_ack)
                    print("recieved ack ", header.seq_num)
                    # Ignore random start messages
                    if header.type == util.START:
                        pass

                    elif header.seq_num == len(chunks):
                        return
                    # TODO double ack
                    # do window logic
                    elif header.seq_num > self.send_base:
                        # Can't think of an instance where the send_base could only increment +1. Think the receiver covers this
                        # TODO check all of window has been sent
                        self.send_base = header.seq_num
                        if self.send_base > len(chunks):
                            break
                        start_time = self.send_window(chunks, sent, start_time)

            except BlockingIOError:
                pass
            except CorruptPacket:
                print("corrupt packet")

            if time.time() - start_time >= ret_time:
                # TODO start_time
                print("enter timeout")
                start_time = self.send_window(chunks, sent, start_time)

    def send_window(self, chunks, sent, start_time):
        range_end = self.send_base + self.window_size
        # TODO check for off by one error
        if range_end > len(chunks):
            range_end = len(chunks)
        for i in range(self.send_base, range_end):
            self.send_packet(util.DATA, chunks[i], i)
            start_time = time.time()
            sent.append(i)
            print(i)
        return start_time

    def close(self):
        """
        Invoked by sender
        Finish the connection and release resources. For simplicity, assume that
        after a socket is closed, neither futher sends nor receives are allowed.
        """
        end_timeout = time.time()
        # TODO check end packet number
        self.send_packet(util.END, "", self.recv_base + 1)
        print("sent end ack")
        while True:
            try:
                return_packet, _ = self.recvfrom(PACKET_SIZE)
                if return_packet:
                    header, _ = unpack(return_packet)
                    if header.type == util.END_ACK:
                        return
            except BlockingIOError:
                pass
            except CorruptPacket:
                pass
            if time.time() - end_timeout >= ret_time:
                self.send_packet(util.END, "", self.recv_base + 1)
                end_timeout = time.time()

    def send_ack(self, msg_type):
        self.send_packet(msg_type, "", self.recv_base)
        print("send ack ", self.recv_base)

    def send_packet(self, msg_type, msg, seq_num):
        # time.sleep(5)
        pkt_header = PacketHeader(type=msg_type, seq_num=seq_num, length=len(msg))
        checksum = compute_checksum(pkt_header / msg)
        pkt_header.checksum = checksum
        pkt = pkt_header / msg
        self.sendto(bytes(pkt), self._send_to)


class Buffer(PriorityQueue):
    """
    Implementation of a priority queue with the ability to peek for the buffer
    """

    def peek(self):
        # Get priority of the buffer
        try:
            return self.queue[0][0]
        except IndexError:
            return None


class CorruptPacket(Exception): pass
