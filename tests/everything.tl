#pragma version 8

# This example aims to use as many tealish language constructs as possible.
# It is used to identify changes in the parser or compiler.
# It should always compile but not necessarily do anything sensible when run.

# A comment below a blank line

# A struct
struct Item:
    id: int
    foo: int
    name: bytes[10]
end

# Consts
const int FOO = 100
const bytes BAR = "bar"

# Assignments
int a = FOO
bytes b = BAR


# Structs
Item item1 = bzero(46)
item1.id = 123
item1.name = "xyz"
assert(item1.id > 0)
log(item1.name)

# Delcaration without assignment
int balance
int exists
# Multiple assignment
# Opcode with immediate arg
exists, balance = asset_holding_get(AssetBalance, 0, 5)
# Use of _ to ignore a return value
_, balance = asset_holding_get(AssetBalance, 1, 5)


if FOO > 1:
    log(BAR)
else:
    error()
end

if 1:
    log("a")
elif 2:
    log("b")
else:
    log("c")
end

if 1:
    jump main
end


# Boxes
box<Item> box1 = CreateBox("a")
box1.name = "xyz"
assert(box1.id)


switch Txn.ApplicationArgs[0]:
    "main": main
    "inner_stuff": inner_stuff
    else: fail
end


block main:
    int amount = sum(2, 3)
    transfer(0, amount, Gtxn[-1].Sender, Txn.Accounts[1])

    int sum = teal_sum(2, 3)
    assert(amount == sum)

    int z = add_amount(5)

    int i = 0
    while i < z:
        i = i + 1
    end

    for _ in 1:10:
        i = i + 1
    end

    for x in 1:10:
        log(itob(x))
    end

    int first = 1
    int last = 5 + 5
    # For loop with variables
    for x in first:last:
        log(itob(x))
    end

    # Function with multiple return values
    int fx
    int fy
    fx, fy = foo(1, 2)

    exit(1)

    # Locally scoped function using variable from parent scope
    func add_amount(x: int) int:
        int result = amount + x
        return result
    end
end


block inner_stuff:
    inner_group:
        inner_txn:
            TypeEnum: Pay
            Receiver: Txn.Sender
            Amount: 1
            Fee: 0
        end
        if 1:
            inner_txn:
                TypeEnum: Axfer
                AssetReceiver: Txn.Sender
                AssetAmount: 1
                XferAsset: 1
                Fee: 0
            end
        end
    end
    exit(1)
end

block fail:
    oops()
end

# Function with no args or return value
func oops():
    error()
    return
end


# Function with args but no return value
func transfer(asset_id: int, amount: int, sender: bytes, receiver: bytes):
    if asset_id == 0:
        inner_txn:
            TypeEnum: Pay
            Sender: sender
            Receiver: receiver
            Amount: amount
            Fee: 0
        end
    else:
        inner_txn:
            TypeEnum: Axfer
            Sender: sender
            AssetReceiver: receiver
            AssetAmount: amount
            XferAsset: asset_id
            Fee: 0
        end
    end
    return
end

# Function with return value
func sum(x: int, y: int) int:
    int result = x + y
    return result
end


func teal_sum(x: int, y: int) int:
    push(x)
    push(y)
    teal:
        pop
        pop
        +
    end
    int result = pop()
    return result
end


# Function with multiple return values
func foo(x: int, y: int) int, int:
    return x, y
end
