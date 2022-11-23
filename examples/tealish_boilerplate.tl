#pragma version 7

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
    # Handle Opt In
    # some statements here
    # exit(1)

    # OR
    # Disallow Opt In
    exit(0)
end

block close_out:
    # Handle Close Out
    # some statements here
    # exit(1)

    # OR
    # Disallow Closing Out
    exit(0)
end

block update_app:
    # Handle Update App
    # Example: Only allow the Creator to update the app
    # exit(Txn.Sender == Global.CreatorAddress)
    # exit(1)

    # OR
    # Disallow Update App
    exit(0)
end

block delete_app:
    # Handle Delete App
    # Example: Only allow the Creator to update the app
    # exit(Txn.Sender == Global.CreatorAddress)
    # exit(1)

    # OR
    # Disallow Delete App
    exit(0)
end

block main:
    switch Txn.ApplicationArgs[0]:
        "method_a": method_a
        "method_b": method_b
        "method_c": method_c
    end

    block method_a:
        # Handle method_a
        # some statements here
        exit(1)
    end

    block method_b:
        # Handle method_b
        # some statements here
        exit(1)
    end

    block method_c:
        # Handle method_c
        # some statements here
        exit(1)
    end

    exit(1)
end
