#pragma version 8

struct Item:
    id: int
    owner: bytes[32]
    content: bytes[100]
end

if Txn.ApplicationID == 0:
    # Handle Create App
    exit(1)
end

switch Txn.OnCompletion:
    NoOp: main
    OptIn: opt_in
    CloseOut: close_out
    UpdateApplication: update_app
    DeleteApplication: delete_app
end

block opt_in:
    # Disallow Opt In
    exit(0)
end

block close_out:
    # Disallow Closing Out
    exit(0)
end

block update_app:
    # Handle Update App
    # Only allow the Creator to update the app
    assert(Txn.Sender == Global.CreatorAddress)
    exit(1)
end

block delete_app:
    # Handle Delete App
    # Only allow the Creator to delete the app
    assert(Txn.Sender == Global.CreatorAddress)
    exit(1)
end

block main:
    switch Txn.ApplicationArgs[0]:
        method("setup()void"): setup
        method("add(uint64,uint64)uint64"): add
        method("mulw(uint64,uint64)uint128"): mulw
        method("hello(string)string"): hello
        method("send(address)void"): send
        method("store_data(byte[10],byte[100])void"): store_data
        method("store_tuple(byte[10],(uint64,address,byte[100]))void"): store_tuple
        method("balance(account)uint64"): balance
    end

    block setup:
        # Do some setup stuff here
        exit(1)
    end

    block add:
        # Add 2 integers
        int x = btoi(Txn.ApplicationArgs[1])
        int y = btoi(Txn.ApplicationArgs[2])
        int result = x + y
        abi_return(abi_encode_uint64(result))
        exit(1)
    end

    block mulw:
        # Multiply 2 integers, returing a uint128
        bytes x = Txn.ApplicationArgs[1]
        bytes y = Txn.ApplicationArgs[2]
        bytes result = x b* y
        abi_return(abi_encode_uint128(result))
        exit(1)
    end


    block hello:
        # Return a greeting
        bytes name = abi_decode_string(Txn.ApplicationArgs[1])
        bytes result = concat("Hello ", name)
        abi_return(abi_encode_string(result))
        exit(1)
    end

    block send:
        # Send some Algo to the given address
        bytes address = Txn.ApplicationArgs[1]
        inner_txn:
            TypeEnum: Pay
            Receiver: address
            Amount: 10000000
            Fee: 0
        end
        exit(1)
    end

    block store_data:
        # Store some fixed size data in a box with the specified key
        bytes key = Txn.ApplicationArgs[1]
        bytes data = Txn.ApplicationArgs[2]
        box_put(key, data)
        exit(1)
    end

    block store_tuple:
        # Store some structured data in a box with the specified key
        bytes key = Txn.ApplicationArgs[1]
        Item data = Txn.ApplicationArgs[2]
        # make some assertion about the data for the fun of it
        assert(data.owner == Txn.Sender)
        box_put(key, data)
        exit(1)
    end

    block balance:
        # Return balance of the specified account
        int result = balance(Txn.Accounts[btoi(Txn.ApplicationArgs[1])])
        abi_return(abi_encode_uint64(result))
        exit(1)
    end
end

func abi_return(result: bytes):
    log(concat("\x15\x1f\x7c\x75", result))
    return
end

func abi_decode_string(value: bytes) bytes:
    # return the content portion of the string, skipping the first 2 bytes which encode the length
    return extract(2, 0, value)
end

func abi_encode_string(value: bytes) bytes:
    # return the bytestring with a uint16 prefix denoting the length
    return concat(extract(6, 2, itob(len(value))), value)
end

func abi_encode_uint64(value: int) bytes:
    return itob(value)
end

func abi_encode_uint32(value: int) bytes:
    # return the last 4 bytes
    return extract(4, 4, itob(value))
end

func abi_encode_uint16(value: int) bytes:
    # return the last 2 bytes
    return extract(6, 2, itob(value))
end

func abi_encode_uint8(value: int) bytes:
    # return the last 1 byte
    return extract(7, 1, itob(value))
end

func abi_encode_uint128(value: bytes) bytes:
    # return 16 bytes with zero padding
    return bzero(16) b| value
end