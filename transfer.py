# spids

# download
(TRANSFER_REQUEST,	# size in bytes (32 bit), name (count prefixed), type (byte)
TRANSFER_REPLY,		# status (byte)
TRANSFER_DATA,		# data
TRANSFER_RESULT, 	# status
TRANSFER_DONE,		# send checksum
# results
REQUEST_OK, REQUEST_TOOBIG, TRANSFER_BUSY,  REQUEST_DENIED, # from request
TRANSFER_OK, CHECK_ERROR, TRANSFER_INCOMPLETE, UNSUPORTED_TYPE, TRANSFER_COMPLETE, # from transfer
# types
UNKNOWN, JAM_PLAYER, JBC_PLAYER, TEXT_TRANSFER, BINARY_TRANSFER,
# upload
TRANSFER_FILE, # file name, type > reply with size and checksum
TRANSFER_CHUNK, # address, size > address (32), size (32), data
FILE_UNAVAILABLE, # either the file name is wrong or resource unavailble
TRANSFER_ABORT
) = range (0,23)

resultText = {
	REQUEST_OK:'REQUEST_OK',
	REQUEST_TOOBIG:' REQUEST_TOOBIG',
	TRANSFER_BUSY:' TRANSFER_BUSY',
	TRANSFER_OK:' TRANSFER_OK',
	CHECK_ERROR:' CHECK_ERROR',
	TRANSFER_INCOMPLETE:' TRANSFER_INCOMPLETE',
	UNSUPORTED_TYPE:'UNSUPORTED_TYPE',
	FILE_UNAVAILABLE:'FILE_UNAVAILABLE',
	REQUEST_DENIED:'REQUEST_DENIED'}

'''
Downloads:
 - initiated from host end
 
  Host         Target          Parameters
   Request----->               size, name, type
      <--------Reply
   Data-------->               address, data
      <--------Result
         ...
   Done-------->               checksum
      <--------Complete

Uploads:
 - initiated from host end
 
  Host         Target          Parameters
   File-------->               name
      <--------Data            address, data
   Result------>
         ...
      <--------Done            checksum
''' 