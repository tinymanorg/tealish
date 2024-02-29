#pragma version 8

if Txn.ApplicationID == 0:
    # Handle Create App
    exit(1)
end

router:
    method_a
    method_b
    method_c
    update_app
    delete_app
end

@public(OnCompletion=UpdateApplication)
func update_app():
    # Handle Update App
    # Example: Only allow the Creator to update the app (useful during development)
    assert(Txn.Sender == Global.CreatorAddress)
    # OR Disallow Update App by removing this function
    return
end

@public(OnCompletion=DeleteApplication)
func delete_app():
    # Handle Delete App
    # Example: Only allow the Creator to update the app (useful during development)
    assert(Txn.Sender == Global.CreatorAddress)
    # OR Disallow Delete App by removing this function
    return
end

@public()
func method_a(user_address: bytes[32], amount: int):
    # Handle method_a
    # some statements here
    return
end

@public()
func method_b():
    # Handle method_b
    # some statements here
    return
end

@public()
func method_c():
    # Handle method_c
    # some statements here
    return
end
