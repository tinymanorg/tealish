inner_txn:
    TypeEnum: Appl
    OnCompletion: NoOp
    ApplicationID: THE_APP_ID
    ApplicationArgs[0]: "arg1"
    ApplicationArgs[1]: "arg2"
    Accounts[0]: Txn.Sender
    Accounts[1]: Txn.Accounts[1]
    Fee: 0
end