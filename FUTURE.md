# Future
This document contains some ideas about potential language features for Tealish. Nothing here is set in stone. These are provided as discussion points and to given an idea of the potential future direction of the language.


## Structs 
Data can be packed into byte strings and read in contracts using the extract* opcodes. This is commonly used for storing data in global and local states and while passing information into contracts through application arguments. Storing structured information in byte strings will become even more common with Boxes.

Currently the developer needs to manually keep track of the offsets and sizes of each piece of data in the byte string and extract and replace them using the relevant opcodes.  There is an opportunity here to extract a common pattern and provide some syntactic sugar to make this more readable.

Consider an example of the following data packed into a byte string:
```
asset_id: uint64
price: uint64
royalty: uint64
seller: bytes[32]
royalty_address: bytes[32]
round: uint64
```

Currently a developer should read these from a byte strings, `data`, as follows:
```
int asset_id = extract_uint64(data, 0)
int price = extract_uint64(data, 8)
int royalty = extract_uint64(data, 16)
bytes seller = extract3(data, 24, 32)
bytes royalty_address = extract3(data, 56, 32)
int round = extract_uint64(data, 88)
```

In Tealish we could introduce a `struct` that allows specifying the schema of a byte string and enables easily accessing and modifying the data:

```
struct Item:
  asset_id: int
  price: int
  royalty: int
  seller: bytes[32]
  royalty_address: bytes[32]
  round: int
end


Item item = Txn.ApplicationArgs[1]
assert(item.asset_id)
assert(item.price > min_price)
assert(item.royalty < max_royalty)
item.round = Global.Round
app_global_put(key, item)
```

At compile time the `struct` accessors would be written with `extract*` opcodes and `replace*` would be used for setting values. There is no runtime computation involved in this approach because all offsets and sizes are known at compile time.


## Boxes

Boxes will need a similar mechanism to `struct`s for reading and writing data in a structured way. Indeed we can directly use structs:

```
Item item = box_get(key)
assert(item.asset_id)
...
item.round = Global.Round
box_put(item)
```

However boxes support larger sizes than bytes on the stack so sometimes it is necessary to use `box_extract` & `box_replace` to read/write portions of the box data.
This will require Tealish to output different Teal while working with boxes.

One option is to define something like `struct` but for boxes:

```
box_struct BoxItem:
  asset_id: int
  description: bytes[100]
  seller: bytes[32]
  price: int
  royalty: int
end

bytes key = "123"

BoxItem item1 = OpenBox(key)
assert(item1.asset_id)
item1.description = "foo"

```
These would work like `struct` but use the `box_extract` & `box_replace` opcodes.

Another approach may be to use `struct` directly and to signal to Tealish that a box has a schema defined by a `struct`:

```
struct Item:
  asset_id: int
  description: bytes[100]
  seller: bytes[32]
  price: int
  royalty: int
end

bytes key = "123"

box[Item] item1 = OpenBox(key)
assert(item1.asset_id)
item1.description = "foo"
```

This approach may be clearer for the developer and may allow better internal code reuse between boxes and structs.

An alternative possible syntax:
```
box Item item2 = CreateBox(key)
item2.asset_id = 2
item2.description = "foo"
```

Notes:
- `CreateBox` will assert that the box did not previously exist
- `OpenBox` requires that the box already exists
- Structs could contain structs
- Box Structs could contain structs



## Types
We might possibly support additional types on top of the AVM types `int` & `bytes`.
Operator overloading might be possible but should be considered very carefully.
e.g. `
```
bytes s = "abc" + "def"

bigint a = 18446744073709551615
bigint b = 100
bigint result = a * b

```

Static types should be preferred to dynamically sized types. We might avoid support for dynamically sized types if at all possible because they require runtime inspection and computation.


### Arrays

Int Arrays

```
int[12] array = Txn.ApplicationArgs[1]
int result = array[0] + array[1]
array[0] = 1

result = 0
foreach x in array:
  result = result + x


int[2] slice = array[2:4]
```

Byte Arrays

```
type bytes10 bytes[10]

bytes10[12] array = Txn.ApplicationArgs[1]

# new bytes string from two values
bytes result = concat(array[0], array[1])

# new array from two values
bytes10[2] array2 = concat(array[0], array[1])

array[0] = "abc"

result = ""
foreach x in array:
  result = concat(result, x)
```

We would need to implement the following:
- array declaration
- array assignment
- array element assignment
- array element access
- array iteration
- array slices


## Public Methods

Many contracts implicitly or explicitly have the concept of methods or operations that can be 'called' by clients. The convention has been to use the first application argument to signify the method name (this is required in ARC4 compliant contracts). It could be useful to define a Tealish language feature for methods that differentiates them from `func` and `block`. 

A `method` would be similar to a `func` but with the restriction that it can only be called from a `router`. It could not be called from other `method`s or `func`s. The `router` would be responsible for routing to the correct `method` based on the first arg and for converting the remaining arguments into the types expected by the `method` signature (e.g. `btoi(Txn.ApplicationArgs[1])` for an argument of type `int`). Additionally the router would be responsible for handling any return value of the `method` and logging as appropriate. 

`method`s should be different from `func`s and have the restriction that they cannot be called by other methods to allow for efficient and safe reuse of slots for variables.

It might be possible to have multiple router implementations adhering to different standards _if necessary_.

The router would be called explicitly somewhere in the program, possibly in multiple execution paths. This would allow for complex logic that is common to multiple methods. `method`s could be defined within `block`s to take advantage of scoping rules where necessary.

When `method`s are used Tealish or external tools could inspect the `method` signatures to generate documentation & machine readable specifications (e.g for ABI).

It would never be required for a Tealish program to use `method`s, just as it is not required for a Teal program to be ABI compatible.


A rough example with methods and a router and some potential decorator syntax for specifying group transaction requirements:

```

if Txn.OnCompletion == NoOp:
    abi_router()
else:
    ...

method bootstrap(asset_1_id: asset, asset_2_id: asset):
    ...
    return
end


@require_txn(Axfer, -1)
method swap(pool_address: account, asset_1_id: asset, asset_2_id: asset, mode: bytes, min_output: int) int:
    ....
    return output_amount
end

```
