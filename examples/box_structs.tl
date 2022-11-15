#pragma version 8

struct Item:
    id: int
    foo: int
    name: bytes[10]
    description: bytes[20]
end

Item item1 = bzero(46)

item1.id = 123
item1.foo = 999
item1.name = "abc"
item1.description = "ABCDEF"

box_put("a", item1)


# int created = box_create("a", 46)
# assert(created)
# created = box_create("a", 46)
# assert(!created)

# Create a new Box, fail if exists
# box<Item> item2 = CreateBox("a")

# Open an existing Box, fail if doesn't exist or size doesn't match struct
box<Item> item2 = OpenBox("a")

# Create a reference to an existing Box but don't assert anything about it
# box<Item> item2 = Box("a")

# These modifications use box_replace
item2.id = 001
item2.foo = 111
item2.name = "xyz"
item2.description = "XYZ"

log(concat("id %i", itob(item2.foo)))

log(concat("name ", item2.name))
log(concat("description ", item2.description))

exit(1)