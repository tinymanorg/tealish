#pragma version 8

const bytes RETURN_PREFIX = h"151f7c75"

# TODO: 
#    need method_signature builtin
#    need abi_return builtin: `log(concat(RETURN_PREFIX, abi_encoded(thing)))
#    need abi_decode/abi_encode to encode/decode arguments into abi types


if Txn.ApplicationID == 0:
    exit(1)
end

switch Txn.OnCompletion:
    NoOp: on_call
end

block on_call:
    switch Txn.ApplicationArgs[0]:
        method("add(uint64,uin64)uint64"): add 
    end
end


block add:
    func inner_add(a: int, b: int)int:
        return a + b
    end

    int result = inner_add(btoi(Txn.ApplicationArgs[1]), btoi(Txn.ApplicationArgs[2]))
    log(concat(RETURN_PREFIX, itob(result)))
    exit(1) 
end
