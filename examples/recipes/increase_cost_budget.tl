func increase_cost_budget():
    inner_txn:
        TypeEnum: Appl
        OnCompletion: DeleteApplication
        ApprovalProgram: "\x06\x81\x01"
        ClearStateProgram: "\x06\x81\x01"
        Fee: 0
    end
    return
end
