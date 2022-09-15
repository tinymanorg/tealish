#pragma version 7

if Txn.ApplicationID == 0:
    # Create app
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
    # Only allow the Creator to update the app
    exit(Txn.Sender == Global.CreatorAddress)
end

block delete_app:
    # Only allow the Creator to delete the app
    exit(Txn.Sender == Global.CreatorAddress)
end

block main:
    switch Txn.ApplicationArgs[0]:
        "method_a": method_a
        "method_b": method_b
        "method_c": method_c
    end

    block method_a:
        # some statements here
        exit(1)
    end

    block method_b:
        # some statements here
        exit(1)
    end

    block method_c:
        # some statements here
        exit(1)
    end
end
