import tealish.langspec


def generate_avm_rst():
    spec = tealish.langspec.get_active_langspec()
    avm_rst = """.. _AVM:

AVM Reference
=============

This page provides a guide to the fields and functions (opcodes) of the Algorand Virtual Machine.
Please refer to the `official AVM docs <https://developer.algorand.org/docs/get-details/dapps/avm/teal/specification/>`_ for further details.

The content of this page is mostly autogenerated from the Teal language specification.

.. _avm_fields:

Fields
------

"""

    avm_rst += "Transaction Fields\n"
    avm_rst += "^^^^^^^^^^^^^^^^^^\n\n"
    avm_rst += "This section lists all :ref:`fields` available on transactions. They can be accessed from Txn, Gtxn[i], Itxn as described in :ref:`fields`.\n\n"
    for f in sorted(spec.fields["Txn"].keys()):
        avm_rst += f"- Txn.{f}\n"

    avm_rst += "\nGlobal Fields\n"
    avm_rst += "^^^^^^^^^^^^^^^\n\n"
    avm_rst += "This section lists all :ref:`fields` available in the ``Global`` namespace.\n\n"
    for f in sorted(spec.fields["Global"].keys()):
        avm_rst += f"- Global.{f}\n"

    avm_rst += "\n.. _avm_functions:\n"
    avm_rst += "\nFunctions\n"
    avm_rst += "-----------\n\n"
    avm_rst += "This section lists all opcodes available in the AVM and usable in Tealish in a function calling style.\n"
    avm_rst += "Some AVM opcodes are excluded from this list because they don't make sense in the context of Tealish or an alternative interface is provided. These are documented below.\n\n"
    for name, op in sorted(spec.ops.items()):
        if op.ignore:
            continue
        doc = op.doc.replace("\n", "\n   ")
        if not op.is_operator:
            avm_rst += f".. function:: {op.sig}\n"
            avm_rst += "   \n"
            avm_rst += f"   {doc}\n"
            avm_rst += "   \n"
        if op.arg_enum:
            avm_rst += f"   Fields: ``{', '.join(op.arg_enum)}``\n"

    avm_rst += "\n.. _avm_operators:\n"
    avm_rst += "\nOperators\n"
    avm_rst += "----------\n\n"
    avm_rst += "This section lists all AVM operator opcodes that can be used in math/logic expressions in Tealish.\n\n"
    for name in tealish.langspec.operators:
        op = spec.ops[name]
        doc = op.doc.replace("\n", "\n   ")
        avm_rst += f"``{op.sig}``\n"
        avm_rst += f"   {doc}\n"
        avm_rst += "\n"

    avm_rst += """
Unsupported Opcodes
-------------------

Some opcodes are excluded from the above lists because they don't make sense in the context of Tealish or an alternative interface is provided:

``global, txn, txna, txnas, gtxn, gtxna, gtxns, gtxnsas``
    The :ref:`fields` syntax is encouraged instead of the function style.

``itxn_begin, itxn_next, itxn_submit``
    The Tealish ``inner_txn`` construct is encouraged instead.

``callsub, retsub``
    Tealish ``Functions`` are used instead.

``b, bz, bnz, match, switch``
    Tealish ``If/Else``, ``Loops`` or ``switch`` are used instead. Tealish does not support labels so these opcodes cannot be used.

``return``
    ``exit`` is an alias of ``return`` in Tealish and its use is encouraged to avoid confusion with ``return`` in Tealish functions.

``intc, bytec``
    Tealish does not expose the int/bytes constants block and to Tealish code.

"""

    with open("avm.rst", "w") as f:
        f.write(avm_rst)
