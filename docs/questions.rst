.. _questions:

FAQ
===
Which Opcodes does Tealish support?
--------------------------------------

All of them! Most opcodes are not implemented directly in Tealish but instead automatically understood by the compiler from the `langspec.json`. This file can be updated independently of Tealish using the `CLI` to make the compiler aware of opcodes newly added to `go-algorand`. 


Does Tealish support ABI?
-------------------------

Tealish doesn't yet have an ABI (Application Binary Interface) API.
So, Tealish doesn't help you to generate method or contract descriptions automatically.

However, implementing ABI compatible contracts using Tealish is possible. You should follow the
`ABI Conventions <https://developer.algorand.org/docs/get-details/dapps/smart-contracts/ABI/>`_
and generate the description manually.

It is likely that future versions of Tealish will allow for more automated ABI support.

What is the difference between `block` and `func`?
--------------------------------------------------

Similar to high level programming languages, :ref:`functions` get some inputs and return some outputs.
It simply allows using the a code block again and again.
:ref:`blocks` are helpful in managing the application flow.

Technically, TEAL uses
`scratchspace <https://developer.algorand.org/docs/get-details/dapps/avm/teal/#storing-and-loading-from-scratchspace>`_
to temporarily store values. Tealish automatically manages scratchspace usage and assigns a slot to each variables.
:ref:`blocks` and :ref:`functions` have different slot spaces. When a function is called, inputs are copied to reserved
slot spaces of the function and outputs are copied to reserved slot spaces of the caller (block, function or program).

Does Tealish have a stateful and stateless mode?
------------------------------------------------

No, Tealish doesn't have modes. The author is responsible for using appropriate `opcodes <https://developer.algorand.org/docs/get-details/dapps/avm/teal/opcodes/>`_.

Can I use subroutines in Tealish?
---------------------------------

Yes, :ref:`functions` are subroutines under the hood.
