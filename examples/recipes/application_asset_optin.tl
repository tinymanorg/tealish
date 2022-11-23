int asset_id

int is_opted_in
is_opted_in, _ = asset_holding_get(AssetBalance, Global.CurrentApplicationAddress, asset_id)

if is_opted_in == 0:
    inner_txn:
        TypeEnum: Axfer
        Sender: Global.CurrentApplicationAddress
        AssetReceiver: Global.CurrentApplicationAddress
        AssetAmount: 0
        XferAsset: asset_id
        Fee: 0
    end
end
