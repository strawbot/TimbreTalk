(CARD_FW_REQ, # return card type followed by pairs of: app type, app version
CARD_FW_RESP,
FWDB_INVALIDATE, # invalidate a side of firmware
FWDB_REBUILD, # scan for local firmware and update firmware dataabase
FWDB_QUERY_REQ, # ask for versions in database
FWDB_QUERY_BUSY, # cannot answer query - FWDB is busy
FWDB_QUERY_RESP, # return versions of fw in db
FWDB_SCAN_SLOTS, # scan for slot cards
FWDB_SET_CHOICE,  # set choice; next byte following is from memorymaps.h IMAGE_...
FWDB_REBOOT,	# followed by time delay in seconds
FWDB_INVALIDATE_RESP,
FWDB_REBUILD_RESP,
FWDB_SCAN_SLOTS_RESP,
FWDB_SET_CHOICE_RESP,
FWDB_REBOOT_RESP
) = range (15)
