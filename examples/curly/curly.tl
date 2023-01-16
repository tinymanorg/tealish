// pragma version 8


// main Router of program
router:
switch Txn.ApplicationID {
    0: exit(1),
    _:  switch Txn.OnCompletion {
        NoOp: switch Txn.ApplicationArgs[0] {
            method(add): add,
            method(sub): sub, 
            method(mul): mul, 
            method(div): div, 
            method(q_rem): q_rem, 
        },
        UpdateApplication|DeleteApplication: exit(Txn.sender == Global.creator_address),
    },
}

func add(a: uint64[int], b: uint64[int]) uint64 {
    return a + b
}
func sub(a: uint64[int], b: uint64[int]) uint64 {
    return a - b
}
func mul(a: uint64[int], b: uint64[int]) uint64 {
    return a * b
}
func div(a: uint64[int], b: uint64[int]) uint64 {
    return a / b
}
func q_rem(a: uint64[int], b: uint64[int]) (uint64,uint64) {
    return [a / b, a % b]
}