# check sum
def fletcher32(address, length): # fletcher 32 bit
	sum1 = sum2 = 0
	for i in range(length):
		sum1 += address[i]
		sum2 += sum1
	return ((sum2 & 0xFFFF) << 16)|(sum1 & 0xFFFF)
