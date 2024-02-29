.. _stdlib:

Standard Library
================

In addition to the AVM opcodes Tealish provides some builtin utility functions.
All builtin Tealish functions are Capitalized to distinguish them from the AVM functions which are lowercase.


.. function:: Cast(Expression, Type) -> any
   
    Tells the compiler to treat the expression as the given type. 
    The compiler adds a runtime type length assertion.

    .. code-block::

        bytes[32] address = Cast(Txn.ApplicationArgs[0], bytes[32])


.. function:: UncheckedCast(Expression, Type) -> any
   
    Tells the compiler to treat the expression as the given type. 
    The compiler *does not* add any runtime type length assertion.

    .. code-block::
        
        bytes[32] address = UncheckedCast(Txn.ApplicationArgs[0], bytes[32])


.. function:: Concat(bytes, bytes, ...,) -> bytes
   
    Concatenates multiple byte strings together.
 
    .. code-block::

        bytes foo = Concat(a, b, c, d)


.. function:: Rpad(bytes, len) -> bytes
   
    Pads the byte string with 0 bytes ("\\x00") to the right.

    .. code-block::

        bytes[10] b = Rpad("abc", 10)
        assert(b == "abc\x00\x00\x00\x00\x00\x00\x00")


.. function:: Lpad(bytes, len) -> bytes
   
    Pads the byte string with 0 bytes ("\\x00") to the left.

    .. code-block::

        bytes[10] b = Lpad("abc", 10)
        assert(b == "\x00\x00\x00\x00\x00\x00\x00abc")


.. function:: SizeOf(Struct) -> int
   
    Returns the size of a ``struct`` type as a compile time constant.

    .. code-block::

        Item item1 = bzero(SizeOf(Item))


.. function:: Address(address) -> bytes
   
    Supports hardcoding of address constants in contracts in the standard Algorand base32 format.
    Note: the address must be a constant at compile time.

    .. code-block::

        const TINYMAN = Address("RIKLQ5HEVXAOAWYSW2LGQFYGWVO4J6LIAQQ72ZRULHZ4KS5NRPCCKYPCUU")


