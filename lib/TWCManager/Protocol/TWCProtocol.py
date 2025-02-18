import logging
import re

logger = logging.getLogger(__name__.rsplit(".")[-1])

class TWCProtocol:

    # To avoid a situation where we would have to re-implement TWCManager logic to parse the
    # same messages both for the Dummy interface and for the Slave TWCManager mode, we break out
    # parsing of the protocol to this module.

    # The operationMode parameter determines which mode the parser operates in:
    #   1 = Slave
    #   2 = Master (not currently implemented)

    master = None
    masterTWCID = None
    operationMode = 0

    def __init__(self, master):
        self.master = master
        self.operationMode = 0
        classname = self.__class__.__name__

    def createMessage(self, packet):

        if packet["Command"] == "SlaveHeartbeat":
            msg = (
                bytearray(b"\xFD\xE0")
                + packet["SenderID"]
                + packet["RecieverID"]
                + bytearray(b"\x00\x00\xa0\x00\x00\x00\x00")
            )
            if self.master.protocolVersion == 2:
                msg += bytearray(b"\x00\x00")

            return msg

        elif packet["Command"] == "SlaveLinkready":
            msg = (
                bytearray(b"\xFD\xE2")
                + packet["SenderID"]
                + packet["Sign"]
                + packet["Amps"]
                + bytearray(b"\x00\x00\x00\x00\x00\x00")
            )
            if self.master.protocolVersion == 2:
                msg += bytearray(b"\x00\x00")

            return msg

    def parseMessage(self, msg):

        # Define protocol packet format
        packet = {
            "Command": None,
            "Errors": [],
            "SenderID": None,
            "Match": False
        }

        msgMatch = re.search(
            b'\xfc\xe1(..)(.)\x00\x00\x00\x00\x00\x00\x00\x00+?.*\Z',
            msg,
            re.DOTALL,
        )

        if msgMatch and packet["Match"] == False:
            # Handle linkready1 from master.
            # See notes in send_master_linkready1() for details.
            packet["Match"] = True
            packet["Command"] = "MasterLinkready1"
            packet["SenderID"] = msgMatch.group(1)
            sign = msgMatch.group(2)
            #self.master.setMasterTWCID(senderID)

            # This message seems to always contain seven 00 bytes in its
            # data area. If we ever get this message with non-00 data
            # we'll print it as an unexpected message.
            logger.info(
                "Master TWC %02X%02X Linkready1.  Sign: %s"
                % (packet["SenderID"][0], packet["SenderID"][1], self.master.hex_str(sign))
            )

            # Other than picking a new fakeTWCID if ours conflicts with
            # master, it doesn't seem that a real slave will make any
            # sort of direct response when sent a master's linkready1 or
            # linkready2.

        else:
            msgMatch = re.search(
                b'\xfb\xe2(..)(.)\x00\x00\x00\x00\x00\x00\x00\x00+?.*\Z',
                msg,
                re.DOTALL,
            )
            if msgMatch and packet["Match"] == False:
                # Handle linkready2 from master.
                # See notes in send_master_linkready2() for details.
                packet["Match"] = True
                packet["Command"] = "MasterLinkready2"
                packet["SenderID"] = msgMatch.group(1)
                sign = msgMatch.group(2)
                #master.setMasterTWCID(senderID)

                # This message seems to always contain seven 00 bytes in its
                # data area. If we ever get this message with non-00 data
                # we'll print it as an unexpected message.

                logger.info(
                    "Master TWC %02X%02X Linkready2.  Sign: %s"
                    % (packet["SenderID"][0], packet["SenderID"][1], self.master.hex_str(sign))
                )

            else:
                msgMatch = re.search(
                    b"\A\xfb\xe0(..)(..)(.......+?).\Z", msg, re.DOTALL
                )
            if msgMatch and packet["Match"] == False:
                # Handle heartbeat message from Master.
                # NOTE: This is very much a cut down version of handling of this message for now
                packet["Match"] = True
                packet["Command"] = "MasterHeartbeat"
                packet["SenderID"] = msgMatch.group(1)
                packet["ReceiverID"] = msgMatch.group(2)
                packet["HeartbeatData"] = msgMatch.group(3)


        return packet
