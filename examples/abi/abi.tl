#pragma version 8

const bytes RETURN_PREFIX = h"151f7c75"

# TODO: 
#    need method_signature builtin
#    need abi_return builtin: `log(concat(RETURN_PREFIX, abi_encoded(thing)))
#    need abi_decode/abi_encode to encode/decode arguments into abi types

if Txn.ApplicationID == 0:
    exit(1)
end

block on_call:
    abi_switch:
        method(add): add
    end
end



extern func add(a: U64[int], b: U64[int])uint64:
    return a + b
end

#decode to
"""
block add:
   int a = abi_decode("uint64", Txn.ApplicationArgs[1])
   int b = abi_decode("uint64", Txn.ApplicationArgs[2])

   int result = do_add(a, b)

   log(concat(RETURN_PREFIX, abi_encode("uint64", (result)))
   exit(1) 

   func do_add(a: int, b: int)int:
       return a + b
   end
end
"""


struct order:
    symbol: U64[int]
    price: U64[int]
    vol: U64[int]
end

external func place_order(o: order)uint64:
    int remaining = fill_order(order.symbol, order.price, order.vol)

    if remaining>0:
        int sequence_number = add_order(order.symbol, order.price, remaining)
        return sequence_number
    end
    return 0
end

# decodes to:
"""
block place_order:
   order o = abi_decode(abi_tuple(order), Txn.ApplicationArgs[1])
   int result = do_place_order(o)
   log(concat(RETURN_PREFIX, abi_encode("uint64", (result)))
   exit(1) 

   func do_place_order(o: order)int:
      int remaining = fill_order(order.symbol, order.price, order.vol)

      if remaining>0:
          int sequence_number = add_order(order.symbol, order.price, remaining)
          return sequence_number
      end
      return 0
   end
end
"""