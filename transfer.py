# spids
(TRANSFER_REQUEST,	# size in bytes (32 bit), name (count prefixed), type (byte)
TRANSFER_REPLY,		# status (byte)
TRANSFER_DATA,		# data
TRANSFER_RESULT, 	# status
TRANSFER_DONE,		# send checksum
# results
REQUEST_OK, REQUEST_TOOBIG, TRANSFER_BUSY, # from request
TRANSFER_OK, CHECK_ERROR, TRANSFER_INCOMPLETE, UNSUPORTED_TYPE, # from transfer
# types
UNKNOWN, JAM_PLAYER, JBC_PLAYER, TEXT_TRANSFER,
# upload
TRANSFER_FILE, # file name, type > reply with size and checksum
TRANSFER_CHUNK, # address, size > address (32), size (32), data
FILE_UNAVAILABLE # either the file name is wrong or resource unavailble
) = range (0,19)

resultText = {
	REQUEST_OK:'REQUEST_OK',
	REQUEST_TOOBIG:' REQUEST_TOOBIG',
	TRANSFER_BUSY:' TRANSFER_BUSY',
	TRANSFER_OK:' TRANSFER_OK',
	CHECK_ERROR:' CHECK_ERROR',
	TRANSFER_INCOMPLETE:' TRANSFER_INCOMPLETE',
	UNSUPORTED_TYPE:'UNSUPORTED_TYPE',
	FILE_UNAVAILABLE:'FILE_UNAVAILABLE'}
