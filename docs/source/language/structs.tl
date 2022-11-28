struct Item:
    x: int
    y: int
    name: bytes[10]
end

Item item1 = Txn.ApplicationArgs[0]
log(item.name)
assert(item.x > 10)
item.y = 1
