#pragma version 9

router:
    method_a
    method_b
    update_app
    delete_app
end

@public(OnCompletion=UpdateApplication)
func update_app():
    assert(Txn.Sender == Global.CreatorAddress)
    return
end

@public(OnCompletion=DeleteApplication)
func delete_app():
    assert(Txn.Sender == Global.CreatorAddress)
    return
end

# a public decorator with the default OnCompletion=NoOp
@public()
func method_a(user_address: bytes[32], amount: int):
    # some statements here
    return
end

@public()
func method_b() int:
    # this value will be logged by the router as an arc4 style return value
    return 42
end
