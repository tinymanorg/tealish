struct Item:
    id: int
    foo: int
    name: bytes[10]
end

box<Item> item1 = CreateBox("a")

item1.id = 1
item1.foo = 111
item1.name = "Tealish   "

log(item1.name)