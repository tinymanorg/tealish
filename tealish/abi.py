from algosdk.abi import ABIType
from .expression_nodes import Bytes, BaseNode


"""
Ints
-----

# should all be 255
int my_int = abi_decode("uint64", "0x00000000000000FF")
int my_int = abi_decode("uint32", "0x000000FF")
int my_int = abi_decode("uint16", "0x00FF")

int my_int = 255
# "0x00000000000000FF"
bytes my_encoded_int = abi_encode("uint64", my_int)
# "0x000000FF"
bytes my_encoded_int = abi_encode("uint32", my_int)
# "0x00FF"
bytes my_encoded_int = abi_encode("uint16", my_int)


Strings
--------

# the abi encoded string 'AB', uint16 len + bytes
# mystring should be == "AB"
bytes my_str = abi_decode("string" "0x00026566")


Tuples
------
# todo: rn the fields are _just_ int/bytes, how do we specify from abi types?
struct custom_struct
    a: uint16 
    b: uint16
end

custom_struct my_struct = abi_decode(abi_tuple(custom_struct), "0x00FF0001")
assert my_struct.a == 255
assert my_struct.b == 1 

Static Arrays
--------------

# static array of ["A", "B"] should decode to 2 byte strings 
[2]bytes my_str_array = abi_decode("[2]string", "0x000165000166")

Dynamic Arrays
---------------

"""


class TealishABIType:
    def __init__(self, type_spec: str):
        # Get the type spec from the abi
        self.sdk_type = ABIType.from_string(type_spec)

    def encode(self, val: BaseNode) -> Bytes:
        # from the `sdk_type`, figure out how to
        # encode the value using TEAL
        pass

    def decode(self, val: Bytes) -> BaseNode:
        # from the `sdk_type`, figure out how to
        # decode the value using TEAL
        pass
