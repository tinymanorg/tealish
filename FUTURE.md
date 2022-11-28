# Future
This document contains some ideas about potential language features for Tealish. Nothing here is set in stone. These are provided as discussion points and to given an idea of the potential future direction of the language.


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


## Public Methods/Externals

Many contracts implicitly or explicitly have the concept of methods/operations/external functions that can be 'called' by clients. The convention has been to use the first application argument to signify the method name (this is required in ARC4 compliant contracts). It could be useful to define a Tealish language feature to identify external functions.

A external function would be similar to other `func`s but with the restriction that it can only be called from a `router`. It could not be called from other `func`s. The `router` would be responsible for routing to the correct function based on the first arg and for converting the remaining arguments into the types expected by the `func` signature (e.g. `btoi(Txn.ApplicationArgs[1])` for an argument of type `int`). Additionally the router would be responsible for handling any return value of the function and logging as appropriate. 

It might be possible to have multiple router implementations adhering to different standards _if necessary_.

The router would be called explicitly somewhere in the program, possibly in multiple execution paths. This would allow for complex logic that is common to multiple methods. External functions could be defined within `block`s to take advantage of scoping rules where necessary.

When external functions are used Tealish or other tools could inspect the function signatures to generate documentation & machine readable specifications (e.g for ABI).

It would never be required for a Tealish program to use external functions, just as it is not required for a Teal program to be ABI compatible.


A rough example with external functions and a router and some potential decorator syntax for specifying group transaction requirements:

```

if Txn.OnCompletion == NoOp:
    abi_router:
        swap
        add_liquidity
        ...
    end
elif Txn.OnCompletion == Optin:
    abi_router:
        bootstrap
    end
else:
    ...

@external
func bootstrap(asset_1_id: asset, asset_2_id: asset):
    ...
end


@require_txn(Axfer, -1)
@external
func swap(pool_address: account, asset_1_id: asset, asset_2_id: asset, mode: bytes, min_output: int) int:
    ....
    return output_amount
end

```

### To be defined
- What happens when a txn cannot be routed by the router? i.e. `arg[0]` does not match a external function signature.
- Can a router have an `else` route?
- Can we have cascading routers?
- Does the router have to be a terminal statement or can other things happen after the routing.
- What should the syntax of the decorators be?

### Prerequisites
Slot assignment for functions must be reworked to safely and efficiently allocate slots for functions based on the call graph.
The current algorithm requires all functions to have separate slot ranges which is not scalable.


# No Longer Future
Future ideas that have either been implemented or discarded.

## Structs
Implemented in https://github.com/tinymanorg/tealish/pull/11

## Boxes
Implemented in https://github.com/tinymanorg/tealish/pull/12
