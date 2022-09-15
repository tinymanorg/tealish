#pragma version 6

if Txn.OnCompletion == UpdateApplication:
    assert(Txn.Sender == Global.CreatorAddress)
    exit(1)
end

assert(Txn.OnCompletion == NoOp)

int counter = app_global_get("counter")
counter = counter + 1
app_global_put("counter", counter)

if counter == 10:
    inner_txn:
        TypeEnum: Pay
        Receiver: Txn.Sender
        Amount: 10000000
    end
elif counter > 10:
    exit(0)
end

exit(1)
