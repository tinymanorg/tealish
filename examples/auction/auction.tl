#pragma version 6

const byte SELLER_KEY = "seller"
const byte NFT_ID_KEY = "nft_id"
const byte START_TIME_KEY = "start"
const byte END_TIME_KEY = "end"
const byte RESERVE_AMOUNT_KEY = "reserve_amount"
const byte MIN_BID_INCREMENT_KEY = "min_bid_inc"
const byte NUM_BIDS_KEY = "num_bids"
const byte LEAD_BID_AMOUNT_KEY = "bid_amount"
const byte LEAD_BID_ACCOUNT_KEY = "bid_account"


if Txn.ApplicationId == 0:
    jump on_create
end

switch Txn.OnCompletion:
    NoOp: on_call
    DeleteApplication: on_delete
end


block on_create:
    int start_time = btoi(Txn.ApplicationArgs[2])
    int end_time = btoi(Txn.ApplicationArgs[3])

    app_global_put(SELLER_KEY, Txn.ApplicationArgs[0])
    app_global_put(NFT_ID_KEY, btoi(Txn.ApplicationArgs[1]))
    app_global_put(START_TIME_KEY, start_time)
    app_global_put(END_TIME_KEY, end_time)
    app_global_put(RESERVE_AMOUNT_KEY, btoi(Txn.ApplicationArgs[4]))
    app_global_put(MIN_BID_INCREMENT_KEY, btoi(Txn.ApplicationArgs[5]))
    app_global_put(LEAD_BID_ACCOUNT_KEY, Global.ZeroAddress)

    assert((Global.LatestTimestamp < start_time) && (start_time < end_time))
    exit(1)
end


block on_call:
    switch Txn.ApplicationArgs[0]:
        "setup": on_setup
        "bid": on_bid
    end
end


block on_setup:
    assert(Global.LatestTimestamp < app_global_get(START_TIME_KEY))
    # opt into NFT asset -- because you can't opt in if you're already opted in, this is what
    # we'll use to make sure the contract has been set up
    inner_txn:
        TypeEnum: Axfer
        XferAsset: app_global_get(NFT_ID_KEY)
        AssetReceiver: Global.CurrentApplicationAddress
    end
    exit(1)
end


block on_bid:
    int txn_index = Txn.GroupIndex - 1
    int nft_holding = asset_holding_get(AssetBalance, Global.CurrentApplicationAddress, app_global_get(NFT_ID_KEY))
    # the auction has been set up
    assert(nft_holding > 0)
    # the auction has started
    assert(app_global_get(START_TIME_KEY) <= Global.LatestTimestamp)
    # the auction has not ended
    assert(Global.LatestTimestamp < app_global_get(END_TIME_KEY))
    # the actual bid payment is before the app call
    assert(Gtxn[txn_index].TypeEnum == Pay)
    assert(Gtxn[txn_index].Sender == Txn.Sender)
    assert(Gtxn[txn_index].Receiver == Global.CurrentApplicationAddress)
    assert(Gtxn[txn_index].Amount >= Global.MinTxnFee)

    if Gtxn[txn_index].Amount >= (app_global_get(LEAD_BID_AMOUNT_KEY) + app_global_get(MIN_BID_INCREMENT_KEY)):
        if app_global_get(LEAD_BID_ACCOUNT_KEY) != Global.ZeroAddress:
            repay_previous_lead_bidder(app_global_get(LEAD_BID_ACCOUNT_KEY), app_global_get(LEAD_BID_AMOUNT_KEY))
        end
        app_global_put(LEAD_BID_AMOUNT_KEY, Gtxn[txn_index].Amount)
        app_global_put(LEAD_BID_ACCOUNT_KEY, Gtxn[txn_index].Sender)
        app_global_put(NUM_BIDS_KEY, (app_global_get(NUM_BIDS_KEY) + 1))
        exit(1)
    end
    exit(0)
end

block on_delete:
    if Global.LatestTimestamp < app_global_get(START_TIME_KEY):
        # the auction has not yet started, it's ok to delete

        # sender must either be the seller or the auction creator
        assert((Txn.Sender == app_global_get(SELLER_KEY)) || (Txn.Sender == Global.CreatorAddress))

        # if the auction contract account has opted into the nft, close it out
        close_nft_to(app_global_get(NFT_ID_KEY),app_global_get(SELLER_KEY))
        # if the auction contract still has funds, send them all to the seller
        close_account_to(app_global_get(SELLER_KEY))
        exit(1)
    end

    if app_global_get(END_TIME_KEY) <= Global.LatestTimestamp:
        # the auction has ended, pay out assets
            if app_global_get(LEAD_BID_ACCOUNT_KEY) != Global.ZeroAddress:
                if app_global_get(LEAD_BID_AMOUNT_KEY) >= app_global_get(RESERVE_AMOUNT_KEY):
                    # the auction was successful: send lead bid account the nft
                    close_nft_to(app_global_get(NFT_ID_KEY), app_global_get(LEAD_BID_ACCOUNT_KEY))
                else:
                    # the auction was not successful because the reserve was not met: return
                    # the nft to the seller and repay the lead bidder
                    close_nft_to(app_global_get(NFT_ID_KEY), app_global_get(SELLER_KEY))
                    repay_previous_lead_bidder(app_global_get(LEAD_BID_ACCOUNT_KEY), app_global_get(LEAD_BID_AMOUNT_KEY))
                end
            else:
                # the auction was not successful because no bids were placed: return the nft to the seller
                close_nft_to(app_global_get(NFT_ID_KEY), app_global_get(SELLER_KEY))
            end
            # send remaining funds to the seller
            close_account_to(app_global_get(SELLER_KEY))
            exit(1)
    end
    exit(0)
end


func close_nft_to(assetID, account):
    int exists
    exists, _ = asset_holding_get(AssetBalance, Global.CurrentApplicationAddress, assetID)
    if exists == 1:
        inner_txn:
            TypeEnum: Axfer
            XferAsset: assetID
            AssetCloseTo: account
        end
    end
    return
end


func repay_previous_lead_bidder(prev_lead_bidder, prev_lead_bid_amount):
    inner_txn:
        TypeEnum: Pay
        Amount: prev_lead_bid_amount - Global.MinTxnFee
        Receiver: prev_lead_bidder
    end
    return
end


func close_account_to(account):
    if balance(Global.CurrentApplicationAddress != 0):
        inner_txn:
            TypeEnum: Pay
            CloseRemainderTo: account
        end
    end
    return
end
