#pragma version 6

# This code is Tealish port of acution demo.
# It contains minimal code changes. Variable names, and order of assignments are preserved.
# Original Code Reference: https://github.com/algorand/auction-demo
# Algorand Developer Portal Auction Demo: https://developer.algorand.org/docs/get-started/dapps/pyteal/#the-smart-contract


const bytes SELLER_KEY = "seller"
const bytes NFT_ID_KEY = "nft_id"
const bytes START_TIME_KEY = "start"
const bytes END_TIME_KEY = "end"
const bytes RESERVE_AMOUNT_KEY = "reserve_amount"
const bytes MIN_BID_INCREMENT_KEY = "min_bid_inc"
const bytes NUM_BIDS_KEY = "num_bids"
const bytes LEAD_BID_AMOUNT_KEY = "bid_amount"
const bytes LEAD_BID_ACCOUNT_KEY = "bid_account"


if Txn.ApplicationID == 0:
    jump on_create
end

switch Txn.OnCompletion:
    NoOp: on_call
    DeleteApplication: on_delete
    OptIn: fail
    CloseOut: fail
    UpdateApplication: fail
end

block fail:
    # Reject
    exit(0)
end

block on_create:
    int start_time = btoi(Txn.ApplicationArgs[2])
    int end_time = btoi(Txn.ApplicationArgs[3])

    # Fix: Accounts should be passed with Accounts instead of Application Args.
    # app_global_put(SELLER_KEY, Txn.ApplicationArgs[0])
    app_global_put(SELLER_KEY, Txn.Accounts[1])

    app_global_put(NFT_ID_KEY, btoi(Txn.ApplicationArgs[1]))
    app_global_put(START_TIME_KEY, start_time)
    app_global_put(END_TIME_KEY, end_time)
    app_global_put(RESERVE_AMOUNT_KEY, btoi(Txn.ApplicationArgs[4]))
    app_global_put(MIN_BID_INCREMENT_KEY, btoi(Txn.ApplicationArgs[5]))
    app_global_put(LEAD_BID_ACCOUNT_KEY, Global.ZeroAddress)

    assert((Global.LatestTimestamp < start_time) && (start_time < end_time))

    # Approve
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
    # Note: The default fee amount of the inner transaction is the minimum transaction fee.
    # It is possible to set it to 0 thanks to fee pooling.
    exit(1)
end


block on_bid:
    int txn_index = Txn.GroupIndex - 1

    int is_opted_in    
    int ntf_balance

    is_opted_in, ntf_balance = asset_holding_get(AssetBalance, Global.CurrentApplicationAddress, app_global_get(NFT_ID_KEY))
    
    # the auction has been set up
    assert(is_opted_in)
    assert(ntf_balance > 0)

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

        # Approve
        exit(1)
    end

    # Reject
    exit(0)
end

block on_delete:
    if Global.LatestTimestamp < app_global_get(START_TIME_KEY):
        # the auction has not yet started, it's ok to delete

        # sender must either be the seller or the auction creator
        assert((Txn.Sender == app_global_get(SELLER_KEY)) || (Txn.Sender == Global.CreatorAddress))

        # if the auction contract account has opted into the nft, close it out
        close_nft_to(app_global_get(NFT_ID_KEY), app_global_get(SELLER_KEY))

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


func close_nft_to(asset_id: int, account: bytes):
    int is_opted_in
    is_opted_in, _ = asset_holding_get(AssetBalance, Global.CurrentApplicationAddress, asset_id)
    if is_opted_in:
        inner_txn:
            TypeEnum: Axfer
            XferAsset: asset_id
            AssetCloseTo: account
        end
    end
    return
end


func repay_previous_lead_bidder(prev_lead_bidder: bytes, prev_lead_bid_amount: int):
    inner_txn:
        TypeEnum: Pay
        Amount: prev_lead_bid_amount - Global.MinTxnFee
        Receiver: prev_lead_bidder
    end
    return
end


func close_account_to(account: bytes):
    if balance(Global.CurrentApplicationAddress) != 0:
        inner_txn:
            TypeEnum: Pay
            CloseRemainderTo: account
        end
    end
    return
end
