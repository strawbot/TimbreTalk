from protocols.alert2_decode import d, value_decode

class console():
    def ind_translate(self,text):
        self.flow += text
        self.checkAlert2()

    def checkAlert2(self):
        # decoders
        def xnum(pdu):  # return 7 bit number or 15 bit number if first bit is high; plus remainder
            num = pdu[0]
            if num & 0x80:
                num = ((num & 0x7F) << 8) + pdu[1]
                return (pdu[2:], num)
            return (pdu[1:], num)

        def decode(flow):  # b'414C44525432...'
            if len(flow) == 0:
                return 'empty PDU'
            pdu, type = xnum(flow)
            pdu, tlv_length = xnum(pdu)

            defn = d.get(type, '--')
            value = value_decode(type, pdu)

            return 'AL22b {:>2}[ {:0>2x}{} {}[ {} ]]'.format(len(pdu), type, '{' + defn + '}', tlv_length, value)

        report = None
        query = bytearray(list(map(ord, 'AL22b')))
        length = len(query)
        while len(self.flow) >= length + 2:
            index = self.flow.find(query)
            if index == 0:
                pdu, length = xnum(self.flow[length:])
                if len(pdu) < length:
                    return
                report = decode(pdu[:length])
                self.flow = pdu[length:]
            elif index > 0:
                report = self.flow[:index].decode('utf-8', 'replace')
                self.flow = self.flow[index:]
            else:
                return
            self.out(report)