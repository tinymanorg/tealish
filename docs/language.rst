.. _language:

Language Guide
==============

Program Structure
-----------------

A Tealish program has the following structure::

    #pragma version 6

    {Comments}

    {Struct Definitions}

    {Constant Declarations}

    {Statements}

    {Exit Statement}

    {Blocks}

    {Function Definitions}


Comments
--------
All comments begin on a new line and start with ``#``::

    # A comment

Literals
--------

Literal bytes::

    "abc"

Literal Integers (unsigned)::

    42

Constants
---------
Constants must use UPPERCASE names:

.. code-block:: tealish

    const int FOO = 1
    const bytes BAR = "ABC"

Declaration & Assignment
------------------------
Variable names must begin with a lowercase letter: ``[a-z][a-zA-Z0-9_]*``.

Variables can be declared separately from assignment:

.. code-block:: tealish

    int x
    bytes b
    x = 1
    b = "abc"

Or declared and assigned together:

.. code-block:: tealish

    int x = 1
    bytes b = "abc"

Assignments must be of the form: ``{name} = {expression}``.
The spacing around the ``=`` operator is mandatory.

Some opcodes return multiple values. In this case the variables must be declared first:

.. code-block:: tealish

    int exists
    bytes asset_unit_name
    exists, asset_unit_name = asset_params_get(AssetUnitName, asset_id)

Sometimes you will want to ignore one of the return values:

.. code-block:: tealish

    _, asset_unit_name = asset_params_get(AssetUnitName, asset_id)


Expressions
------------------------

Expressions are pieces of Tealish that evaluate to a value. They are not valid statements on their own but are used on the right side of assignments, in conditions and arguments.

.. note:: Statements vs Expressions

    A Tealish statement is a valid standalone line (or lines) of Tealish.
    An expression is something that evaluates to a value. It must be used inside a statement.

Expressions are composed of the following components:
 * Values
 * Function Calls
 * Math/Logic
 * Expression Groups

Values
______

Values are composed of:
 * Literals
 * Constants
 * Variables
 * Fields
 * Builtins

Function Calls
______________
Function calls take the form of ``{name}({expression}, {expression}...)``.
Functions can take 0, 1 or more arguments.
Examples::
    
    sqrt(x)
    app_local_get(address, key)

Function calls are expressions so they are valid arguments to other functions::

    sqrt(sqrt(x))

The same function call syntax is used for opcodes, user defined functions and Tealish builtins.
Functions that do not return values cannot be used as expressions. They can only be used as statements.

OpCodes
_______
Most opcodes (AVM Functions) can be used in a function call style. The syntax is of the following form: ``{op_name}({expression_A}, {expression_B}...)``.
For example ``app_local_get`` is described in the docs as ``local state of the key B in the current application in account A``.
In Tealish this is written as ``app_local_get(account, key)``.

Some opcodes expect "immediate args". For example ``substring`` takes two immediate arguments ``s`` (start), ``e`` (end). In Tealish this is written as ``substring(0, 5)``. 
Some opcodes expect both immediate and stack arguments: e.g ``asset_params_get(AssetUnitName, asset_id)``. It is important to note that immediate arguments cannot be expressions and therefore must be literals.

See :ref:`avm_functions` for the full list of supported function opcodes.



Some opcodes are defined for use as mathematical or logical operators. These are used in the form discussed below.


Math/Logic
__________
Math & Logic are most naturally written with infix notation. Nearly all math & logic expressions are binary expressions of the form ``{expression} {operator} {expression}``.
Spacing around the operator is required. 

Examples::

    1 + 2
    2 * a
    b / 2
    1 == 2
    2 != a
    x > y

As math & logic expressions are all binary expressions it is necessary to use "groups" rather than chaining::

    1 + 2 + 3 # Invalid!
    (1 + 2) + 3 # Valid
    1 + (2 + 3) # Valid

This requirement exists to ensure math and logic is written obviously and unambiguously (from a human reader perspective). 

The exception to the above rule is Unary expressions::

    !x # valid
    x || !y # valid


.. note:: Logical operators ``||`` (or) and ``&&`` (and) in Tealish have AVM stack semantics which differ from some other languages.
    There is no short circuiting with these operators. 
    For example ``x && f(x)`` will still evaluate both ``x`` and ``f(x)`` before evaluating the ``&&`` even if ``x`` is 0.



See :ref:`avm_operators` for the full list of supported math & logic operator opcodes.

.. note:: Operators are not handled the same way as other opcodes in Tealish so the langspec opcode support mechanisms do not apply.

.. _fields:

Fields
------

The AVM provides readonly access to fields in a number of namespaces through opcodes. These include ``global, txn, txna, gtxn, gtxnas, itxn,`` and many more.
Tealish provides a specific syntax for accessing fields to differentiate these from function calls and make the code more readable. The base form of this syntax is ``{Namespace}.{FieldName}``.
The namespace is always the Capitalized version of the corresponding (base) opcode; e..g ``Txn, Gtxn, Itxn, Global``. Fieldnames are also always Capitalized.

For array fields indexing is used to access specific elements: ``{Namespace}.{FieldName}[{Expression}]``. In this case the base opcode is still used as the namespace (e.g `Txn` instead of `Txna`).

Fields from other transactions in the same Group can be accessed with ``Gtxn[{GroupIndex}].{FieldName}[{Expression}]``. 
`GroupIndex` can be an expression or a signed literal (e.g `+1`, `-2`). Signed literals are used for relative indexing.

Examples::

    Global.Round
    Txn.Sender
    Itxn.Fee
    Txn.ApplicationArgs[0]
    Txn.ApplicationArgs[x + 2]
    Gtxn[0].Sender
    Gtxn[payment_txn_index].Receiver
    Gtxn[+1].ApplicationArgs[0]
    Gtxn[-2].Sender

See :ref:`avm_fields` for the full list of fields.


If/Elif/Else
------------

Structure::

    if {condition_Expression}:
        {Statements}
    elif {condition_Expression}:
        {Statements}
    else:
        {Statements}
    end

Examples:

.. code-block:: tealish

    if x < 1:
        result = 1
    elif x < 10:
        result = 2
    else:
        error()
    end

    if x == y:
        result = 1
    end

    if x < 1:
        result = 0
    else:
        result = 1
    end

If statements can be nested:

.. code-block:: tealish

    if x:
        if y:
            error()
        end
    end


While Loop
----------

Structure::

    while {condition_Expression}:
        {Statements}
    end

Examples:

.. code-block:: tealish

    int i = 0
    while i <= 10:
        result = result + Txn.ApplicationArgs[i]
        i = i + 1
    end


For Loop
--------

Structure::

    for {name} in {start}:{end}
        {Statements}
    end

`start` and `end` can be Literals or Variables but not Expressions (for readability).

Examples:

.. code-block:: tealish

    for i in 0:10:
        result = result + Txn.ApplicationArgs[i]
    end

    int start = 0
    int end = start + 10
    for i in start:end:
        result = result + Txn.ApplicationArgs[i]
    end

    # if the loop variable is not used in the body then ``_`` should be used instead.
    for _ in 0:10:
        result = result + "*"
    end

.. _inline_teal:

Inline Teal
-----------

Structure::

    teal:
        {Statements}
    end

Examples:

.. literalinclude:: ./source/language/inline_teal.tl
    :language: tealish


Inner Transactions
------------------

Tealish has a special syntax for Inner Transactions::

    inner_txn:
        {FieldName}: {Expression}
        {FieldName}: {Expression}
        ...
    end

Example:

.. code-block:: tealish

    inner_txn:
        TypeEnum: Pay
        Receiver: Txn.Sender
        Amount: 1000
        Fee: 0
    end

Inner transactions are evaluated immediately so there is no separate submit function.

Inner transactions can be grouped in inner groups:

.. code-block:: tealish

    inner_group:
        inner_txn:
            TypeEnum: Pay
            Receiver: Txn.Sender
            Amount: 1000
            Fee: 0
        end
        inner_txn:
            TypeEnum: Axfer
            AssetReceiver: Txn.Sender
            AssetAmount: 1000
            Index: 5
            Fee: 0
        end
    end

.. _functions:

Functions
---------

Functions can be defined in Tealish in the following forms::

    func {func_name}({arg1_name}: {type}, {arg2_name}: {type}) {return_type}:
        {Statements}
        return {Expression}
    end

    # No return value
    func {func_name}({arg1_name}: {type}, {arg2_name}: {type}):
        {Statements}
        return
    end

    # No return value or arguments
    func {func_name}():
        {Statements}
        return
    end


    # Multiple return values
    func {func_name}() {return_type}, {return_type}:
        {Statements}
        return {Expression}, {Expression}
    end

    # Returns in if & else statements
    func {func_name}() {return_type}, {return_type}:
        {Statements}
        if {Statements}:
            return {Statements}
        else:
            return {Statements}
        end

        # Return is mandatory just before the end statement of the function
        return
    end

Notes:

- Function names must be lowercase.
- Argument names must be lowercase.
- Types must be ``int`` or ``bytes``.
- Functions must have ``return`` just before ``end``.
- Functions must be defined at the end of programs or Blocks. There can be no other statements after function definitions apart from other function definitions.

Examples:

.. literalinclude:: ./source/language/functions.tl
    :language: tealish

.. _blocks:

Blocks
------

Blocks can be defined in Tealish in the following forms::

    block {block_name}:
    {Statements}
    end

Notes:

- Variables are scoped by blocks and functions.
- Blocks should end with an exit statement.

Examples:

.. literalinclude:: ./source/language/blocks.tl
    :language: tealish


.. _switch:

Switch
------

A switch statement is used to conditionally branch to blocks of a program.
Structure::

    switch {condition_Expression}:
        {Value}: {Block_Name}
        {Value}: {Block_Name}
        {Value}: {Block_Name}
        ...
        else: {Block_Name}
    end

Notes:

- If none if the values match the expression then the optional ``else`` target is used if specified, otherwise an error is raised.
- Any code after a ``switch`` is unreachable.

Example:

.. literalinclude:: ./source/language/switch.tl
    :language: tealish


.. _jump:

Jump
----

A jump statement is used to unconditionally branch to a block of a program.

Structure::

    jump({Block_Name})

Notes:

- The block name is a literal, not an expression.
- Any code after a ``jump`` is unreachable.



Structs
-------

Structs are used to define structure for byte strings.

Structs can be defined in Tealish in the following form::

    struct {Struct_name}:
        {field_name}: {type}
    end

Notes:

- Structs must be defined at the top of the file.
- Struct names must begin with a capital letter.
- Field names must be lowercase.
- Types may be either ``int`` or ``bytes[N]``

Examples:

.. literalinclude:: ./source/language/structs.tl
    :language: tealish


.. warning:: There are no implicit runtime checks when assigning to a struct or struct field. Care must be taken to ensure field values are correctly sized.


Boxes
-----

Boxes can be accessed and manipulated using the standard opcodes (``box_put``, ``box_get``, ``box_extract``, etc). 

Tealish also supports a higher level syntax that makes it easier to deal with structured data in boxes using structs_. 
A typed box reference can created with the following forms::

    box<{Struct_name}> {box_name} = CreateBox("{box_key}") # asserts box does not already exist
    box<{Struct_name}> {box_name} = OpenBox("{box_key}")   # asserts box does already exist and has the correct size for the struct
    box<{Struct_name}> {box_name} = Box("{box_key}")       # makes no assertions about the box

A box field can be set or accessed just like a struct field::

    {box_name}.{field_name} = {value}

    log({box_name}.{field_name})


Examples:

.. literalinclude:: ./source/language/boxes.tl
    :language: tealish

.. warning:: There are no implicit runtime checks when assigning to a box field. Care must be taken to ensure field values are correctly sized.
