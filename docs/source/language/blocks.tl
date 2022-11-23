block main:
    int sender = Txn.Sender
    pay_to_user()
    exit(1)

    func pay_to_user(amount: int):
        # Function can use variables defined in the outer blocks.
        pay(sender, amount)
        return
    end
    exit(0)
end

func pay(receiver: bytes, amount: int):
    inner_txn:
        TypeEnum: Pay
        Receiver: receiver
        Amount: amount
        Fee: 0
    end
    return
end