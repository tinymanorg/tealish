.. _recipes:

Recipes
=======


Converting App Argument to `Integer`
------------------------------------

All arguments passed to the application in the ApplicationCall transaction are converted to bytes.
If you passed an integer and want to use it as integer in the contract, you have to convert it to integer using
`btoi <https://developer.algorand.org/docs/get-details/dapps/avm/teal/opcodes/#btoi>`_ opcode.

.. literalinclude:: ../examples/recipes/btoi.tl
   :emphasize-lines: 2
   :linenos:

Opting in the application to an asset
-------------------------------------

.. literalinclude:: ../examples/recipes/application_asset_optin.tl
   :emphasize-lines: 7-14
   :linenos:


Handling Integer Overflow
-------------------------

Converting `integers` to `big-endian unsigned integers` and using
`byte arithmetics <https://developer.algorand.org/docs/get-details/dapps/avm/teal/specification/#byte-array-manipulation>`_
allows handling integer overflows.

.. note::
    Bytes are also have a limit.

.. literalinclude:: ../examples/recipes/overflow.tl
   :emphasize-lines: 7-9
   :linenos:


Can I use subroutines in Tealish?
---------------------------------

Yes, :ref:`functions` are subroutines under the hood.


Optimize the generated TEAL code partially
------------------------------------------

Teal allows using raw TEAL directly, see :ref:`inline_teal`.
Decreasing the size and computational cost using TEAL and custom stack management is possible.

Reformatting the Tealish code may result a `small` gain. Reducing the variable usage help you ascetically if you are on the limit of budget cost.
Variable assignment generates `store,` and usages generates `load` opcodes. So, you can remove the variables used one time.

.. literalinclude:: ../examples/recipes/optimization_a.tl
   :emphasize-lines: 1-5
   :linenos:

.. literalinclude:: ../examples/recipes/optimization_b.tl
   :emphasize-lines: 1
   :linenos:


Increasing the budget
---------------------

All TEAL Opcodes has a computational cost and total opcode budget of an application call is 700 arithmetics.
If the transaction group has multiple application calls, the budget is pooled. The details are explained in the
`Algorand Developer Documentation
<https://developer.algorand.org/docs/get-details/dapps/avm/teal/#dynamic-operational-cost-of-teal-opcodes>`_.

Similar to `OpUp utility of PyTeal <https://pyteal.readthedocs.io/en/latest/opup.html>`_,
you can increase the cost budget by adding another app call using inner transactions.

`increase_cost_budget` creates and deletes an app with single transactions.

.. note::
    This operation increases the minimum balance `temporarily`.

.. literalinclude:: ../examples/recipes/increase_cost_budget.tl
   :linenos: