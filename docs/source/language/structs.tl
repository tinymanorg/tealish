struct Item:
    x: int
    y: int
    name: bytes[10]
end

Item item = Cast(Txn.ApplicationArgs[0], Item)
log(item.name)
assert(item.x > 10)
item.y = 1
