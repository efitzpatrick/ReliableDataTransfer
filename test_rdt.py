import pytest

import rdt
import util
from rdt import *
from unittest.mock import Mock

@pytest.fixture
def bites():
    return b'00112233'


def test_split_bytes(bites):
    sender = rdt
    rdt.PAYLOAD_SIZE = 2
    sender._send_to = True
    actual_return = sender.split_bytes(bites)
    assert actual_return == [b'00', b'11', b'22', b'33']

def test_sender(mocker, bites):
    rdt.PAYLOAD_SIZE = 2
    address = ("192.168.100", 100)
    sender = rdt.RDTSocket(3)
    sender._send_to = True
    send_mock = mocker.patch("util.UnreliableSocket.sendto")
    send_mock.return_value = 1
    #TODO remove below to test fully
    compute_mock = mocker.patch("rdt.compute_checksum")
    compute_mock.return_value = 1

    sender.send(bites)
    assert send_mock.call_count == 4
    assert type(send_mock.call_args[0][0]) is bytes
    # calls = [mocker.call(b'00', address), mocker.call(b'11', address), mocker.call(b'22', address), mocker.call(b'33', address)]
    # send_mock.assert_has_calls(calls, any_order=False)

def test_recv(mocker, bites):
    receiver = rdt.RDTSocket(3)
    receiver._send_to = True
    send_mock = mocker.patch("util.UnreliableSocket.sendto")
    send_mock.return_value = 1
    recv_mock = mocker.patch("util.UnreliableSocket.recvfrom")
    recv_mock.return_value = 2, 0
    verify_mock = mocker.patch("rdt.verify_packet")
    verify_mock.return_value = True
    unpack_mock = mocker.patch("rdt.RDTSocket.unpack")
    unpack_mock.side_effect = [(PacketHeader(type=util.DATA, seq_num=5), b"five "),
                               (PacketHeader(type=util.DATA, seq_num=2), b"two "),
                               (PacketHeader(type=util.DATA, seq_num=3), b"three "),
                               (PacketHeader(type=util.DATA, seq_num=0), b"zero "),
                               (PacketHeader(type=util.DATA, seq_num=1), b"one "),
                               (PacketHeader(type=util.DATA, seq_num=4), b"four "),
                               (PacketHeader(type=util.END, seq_num=4), b"")]
    # TODO remove below to test fully
    compute_mock = mocker.patch("rdt.compute_checksum")
    compute_mock.return_value = 1


    assert receiver.recv(10) == b"zero one two three four five "

def test_send_packet(mocker):
    pass