.. _quick_start:

Quick Start
===========

The Basics
----------

A program must begin with a Teal ``pragma`` line specifying the Teal version.
Tealish programs are executed from top to bottom. 
A programs execution must end with ``exit(1)`` for the transaction to be accepted.
If the program fails with an error or ends with ``exit(0)`` the transaction will be rejected.

.. note:: If you are familiar with Teal or PyTeal, ``exit`` is a Tealish alias for the ``return`` opcode.

The Smallest Tealish Programs
_____________________________

This is the smallest valid Tealish program. It will always approve.
This is unsafe because it will approve any transaction, even an `Application Update <https://developer.algorand.org/docs/get-details/dapps/smart-contracts/apps/#update-smart-contract>`_ or `Application Delete <https://developer.algorand.org/docs/get-details/dapps/smart-contracts/apps/#delete-smart-contract>`_ transaction!

.. literalinclude:: ../examples/minimal.tl
    :language: tealish


This is a minimal immutable Tealish program. It will approve any Application Noop call but reject Update, Delete, etc.

.. literalinclude:: ../examples/minimal_immutable.tl
    :language: tealish


A Simple Tealish Program
________________________

This is a more useful program that demonstrates assertions, state, if statements and inner transactions:

.. literalinclude:: ../examples/counter_prize/counter_prize.tl
   :language: tealish

Refer to the :ref:`language` and :ref:`AVM` to understand what each line of this program does.

The above program has one main piece of functionality and additional logic for creation and updates.
Most programs are more complex than this and require more structure and ability for the caller to specify the method or operation they wish to use.
A common pattern is to 'route' the execution to different parts of the program with :ref:`conditionals` or :ref:`switch` statements.


Tealish Boilerplate
-------------------

The following code shows the common structure used in many larger Tealish programs. It is a good place to start a new project from.

.. literalinclude:: ../examples/tealish_boilerplate.tl
    :language: tealish
    :caption: approval.tl

Every application requires both an `Approval Program and a Clear State Program <https://developer.algorand.org/docs/get-details/dapps/smart-contracts/apps/#the-lifecycle-of-a-smart-contract>`_.
So far we have only shown the Approval Program. In most cases the Clear State program is extremely simple and just accepts. 

.. literalinclude:: ../examples/minimal.tl
    :language: tealish
    :caption: clear.tl


Build Your App
--------------

.. code-block::

    $ tealish compile approval.tl
    $ tealish compile clear.tl

The ``build/`` directory will now contain ``approval.teal`` and ``clear.teal``.


Deploying Your App
------------------

Please see the official `Algorand Docs <https://developer.algorand.org/docs/get-details/dapps/smart-contracts/frontend/apps/>`_ for instructions on deploying the app with the generated Teal files from above.
