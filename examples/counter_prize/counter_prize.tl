#pragma version 8

# ApplicationID will be 0 when the app is being created
if Txn.ApplicationID == 0:
    # Initialise the counter state to 0
    app_global_put("counter", 0)
    exit(1)
end

if Txn.OnCompletion == UpdateApplication:
    # Only allow the Creator to update the app
    assert(Txn.Sender == Global.CreatorAddress)
    exit(1)
end

# Ensure that this is a NoOp application call. Don't allow optin, delete, etc
assert(Txn.OnCompletion == NoOp)

# Read the counter value from state and increment it
int counter = app_global_get("counter")
counter = counter + 1
app_global_put("counter", counter)

if counter == 10:
    # If the counter is 10 make a Payment transaction
    inner_txn:
        TypeEnum: Pay
        Receiver: Txn.Sender
        Amount: 10000000
    end
elif counter > 10:
    # If the counter is past 10 fail the program
    exit(0)
end

# Exit the program with approval
exit(1)
