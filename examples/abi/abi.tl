#pragma version 8

const bytes RETURN_PREFIX = h"151f7c75"

if Txn.ApplicationID == 0:
    jump on_create
end

switch Txn.OnCompletion:
    NoOp: on_call
end


block on_create:
    exit(1)
end

block on_call:
    # TODO: need method selector and auto arg parse?
    switch Txn.ApplicationArgs[0]:
        "add(uint64,uin64)uint64": add 
    end
end


block add:
    func inner_add(a: bytes, b: bytes)bytes:
        return itob(btoi(a) + btoi(b))
    end

    bytes result = inner_add(Txn.ApplicationArgs[1], Txn.ApplicationArgs[2])
    log(concat(RETURN_PREFIX, result))
    exit(1) 
end