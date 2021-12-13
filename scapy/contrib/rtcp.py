# This file is part of Scapy
# See http://www.secdev.org/projects/scapy for more information
# Copyright (C) Pavel Oborin <oborin.p@gmail.com>
# This program is published under a GPLv2 license

# RFC 3550
# scapy.contrib.description = Real-Time Transport Control Protocol
# scapy.contrib.status = loads

import struct

from scapy.packet import Packet, bind_layers, Padding, Raw
from scapy.fields import (
    BitField, ByteEnumField, IntField, ConditionalField,
    PacketListField, BitFieldLenField,
    LongField, PacketField, ByteField,
    X3BytesField, LenField, PacketLenField,
    FieldListField, StrLenField, PadField,
    FieldLenField
)


_rtcp_packet_types = {
    200: 'Sender report',
    201: 'Receiver report',
    202: 'Source description',
    203: 'BYE',
    204: 'APP'
}


class SenderInfo(Packet):
    name = "Sender info"
    fields_desc = [
        LongField('ntp_timestamp', None),
        IntField('rtp_timestamp', None),
        IntField('sender_packet_count', None),
        IntField('sender_octet_count', None)
    ]


class ReceptionReport(Packet):
    name = "Reception report"
    fields_desc = [
        IntField('sourcesync', None),
        ByteField('fraction_lost', None),
        X3BytesField('cumulative_lost', None),
        IntField('highest_seqnum_recv', None),
        IntField('interarrival_jitter', None),
        IntField('last_SR_timestamp', None),
        IntField('delay_since_last_SR', None)
    ]


_sdes_chunk_types = {
    0: "END",
    1: "CNAME",
    2: "NAME",
    3: "EMAIL",
    4: "PHONE",
    5: "LOC",
    6: "TOOL",
    7: "NOTE",
    8: "PRIV"
}


class SDESItem(Packet):
    name = "SDES item"
    fields_desc = [
        ByteEnumField('chunk_type', None, _sdes_chunk_types),
        FieldLenField('length', None, fmt='!b', length_of='value'),
        StrLenField('value', None, length_from=lambda pkt: pkt.length)
    ]

    def extract_padding(self, p):
        return "", p


class SDESChunk(Packet):
    name = "SDES chunk"
    fields_desc = [
        IntField('sourcesync', None),
        PacketListField('items', None, pkt_cls=SDESItem)
    ]


class RTCP(Packet):
    name = "RTCP"

    fields_desc = [
        # HEADER
        BitField('version', 2, 2),
        BitField('padding', 0, 1),
        BitFieldLenField('count', 0, 5, count_of='report_blocks'),
        ByteEnumField('packet_type', 0, _rtcp_packet_types),
        LenField('length', None, fmt='!h'),
        # SR/RR
        ConditionalField(IntField('sourcesync', 0), lambda pkt: pkt.packet_type in (200, 201)),
        ConditionalField(PacketField('sender_info', SenderInfo(), SenderInfo), lambda pkt: pkt.packet_type == 200),
        ConditionalField(PacketListField('report_blocks', None, pkt_cls=ReceptionReport, count_from=lambda pkt: pkt.count), lambda pkt: pkt.packet_type in (200, 201)),
        # SDES
        ConditionalField(PacketListField('sdes_chunks', None, pkt_cls=SDESChunk, count_from=lambda pkt: pkt.count), lambda pkt: pkt.packet_type == 202),
    ]

    def post_build(self, pkt, pay):
        pkt += pay
        if self.length is None:
            pkt = pkt[:2] + struct.pack("!h", len(pkt) // 4 - 1) + pkt[4:]
        return pkt
