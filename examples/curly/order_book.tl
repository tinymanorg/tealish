// pragma version 8

struct IncomingOrder {
    symbol: uint64[int]
    price: uint64[int]
    vol: uint64[int]
    is_buy: bool[int]
}

struct RestingOrder {
    acct: addr[byte[32]]
    seq: uint64[int]
    vol: uint64[int]
    price: uint64[int]
}

struct Book {
    orders: RestingOrder[]
    best: uint64[int] 
}

Box[Book] bids = Box("bids");
Box[Book] asks = Box("asks")

GlobalState[addr[byte[32]]] admin = GlobalState("admin")

// Main Entry and router, single nested flow  
switch Txn.ApplicationID {
    0: on_create,
    _:  switch Txn.OnCompletion {
        NoOp: switch Txn.ApplicationArgs[0] {
            method(place_order): place_order,
            method(cancel_order): cancel_order,
            method(modify_order): modify_order,
        },
        UpdateApplication|DeleteApplication: exit(Txn.sender == Global.creator_address),
    },
}

on_create:
{
    CreateBox(bids) 
    CreateBox(asks) 

    InitState(admin, Txn.sender)
    exit(1)
}


func place_bid(o: IncomingOrder) uint64[int] {
    assert(o.is_bid)
    assert(o.vol>0)
    assert(o.price>0)


    while(o.vol > 0) {
        o.vol -= fill_from_book(ask_book, o.price, o.vol)
    }

    int seq_id = 0
    if (o.vol > 0) {
        seq_id = add_to_book(bid_book, o)
    }
    return seq_id 
}


func place_ask(o: IncomingOrder) uint64[int] {
    assert(o.is_bid)
    assert(o.vol>0)
    assert(o.price>0)

    while(o.vol > 0) {
        o.vol -= fill_from_book(bid_book, o.price, o.vol)
    }

    int seq_id = 0
    if (o.vol > 0) {
        seq_id = add_to_book(ask_book, o)
    }
    return seq_id 
}

func fill_from_book(book: Book, price: int, vol: int) int {
    // Fill each order according to the book state
    // return the number left for incoming volume after filling
}

func add_to_book(book: Book, o: IncomingOrder) int {
    // add to the book based on the price, assign it a sequence number
}
