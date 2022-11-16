#pragma version 7

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

log(concat("id %i", itob(extract_uint64(item1, 0))))


log(concat("id %i", itob(item1.foo)))

log(concat("name ", item1.name))
log(concat("description ", item1.description))

exit(1)