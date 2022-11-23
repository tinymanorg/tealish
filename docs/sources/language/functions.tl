func get_balance(account_idx: int, asset_id: int) int:
    int balance
    if asset_id == 0:
        balance = balance(account_idx) - min_balance(account_idx)
    else:
        _, balance = asset_holding_get(AssetBalance, account_idx, asset_id)
    end
    return balance
end

func checks():
    assert(app_local_get(0, "x") > 7)
    assert(app_local_get(0, "y") > 6)
end
