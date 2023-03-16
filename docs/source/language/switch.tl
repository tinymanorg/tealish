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
    exit(1)
end

block update_app:
    # Handle Update App
    # Example: Only allow the Creator to update the app
    exit(Txn.Sender == Global.CreatorAddress)
end
