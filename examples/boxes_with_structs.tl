#pragma version 8

# This example shows a high level interace to Boxes using box structs.
# There is also the lower level method of directly using box_put, box_get, etc with structs or plain bytes.

struct Item:
    id: int
    foo: int
    name: bytes[10]
end

# Create a new Box with key "a", fail if box already exists
# The size of the box is determined from the Item struct
# The max size of a box is 32K bytes
box<Item> item1 = CreateBox("a")

# OR
# Open an existing Box, fail if doesn't exist or size doesn't match the struct
# box<Item> item1 = OpenBox("a")

# OR
# Create a reference to an existing Box but don't assert anything about it
# box<Item> item1 = Box("a")

# Box field modifications use box_replace so each field value can be up to 4096 bytes in size
item1.id = 1
item1.foo = 111
item1.name = "xyz"

log(itob(item1.foo))

log(concat("name ", item1.name))


# If the total box size is <= 4096 bytes it is possible to use structs and box_put/box_get.
# This is useful for deserialising data from application arguments:
Item item2 = Txn.ApplicationArgs[0]
assert(item2.id > 0)
box_put("a", item2)

exit(1)