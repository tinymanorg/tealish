.. _quick_start:

Quick Start
===========

The Basics
----------

A Tealish program must begin with a Teal ``pragma`` line specifying the Teal version.
Tealish programs are executed from top to bottom. 
A programs execution must end with ``exit(1)`` in order for the transaction to be accepted.
If the program fails with an error or ends with ``exit(0)`` the transaction will be rejected.

.. note:: If you are familiar with Teal or PyTeal, ``exit`` is a Tealish alias for the ``return`` opcode.

The Smallest Tealish Programs
_____________________________

This is the smallest valid Tealish program, which will always approve a transaction.
However, this is unsafe because it will approve any transaction, even an `Application Update <https://developer.algorand.org/docs/get-details/dapps/smart-contracts/apps/#update-smart-contract>`_ or `Application Delete <https://developer.algorand.org/docs/get-details/dapps/smart-contracts/apps/#delete-smart-contract>`_ transaction!

.. literalinclude:: ../examples/minimal.tl
    :language: tealish


This is a minimal immutable Tealish program that approves any Application Noop call, but rejects Update, Delete, etc.

.. literalinclude:: ../examples/minimal_immutable.tl
    :language: tealish


A Simple Tealish Program
________________________

This is a more useful program that demonstrates the use of assertions, state, if statements and inner transactions:

.. literalinclude:: ../examples/counter_prize/counter_prize.tl
   :language: tealish

To understand what each line of this program does, please refer to the :ref:`language` and :ref:`AVM`.

The program above demonstrates one main functionality, along with additional logic for creation and updates.
While this program is relatively simple, most programs are more complex and require additional structure and the ability for the caller to specify the method or operation they wish to use.
A common Tealish pattern is to 'route' the execution to different parts of the program using :ref:`conditionals` or :ref:`switch` statements.


Tealish Boilerplate
-------------------

The following code shows the common structure used in many larger Tealish programs. It is a good starting point for a new project.

.. literalinclude:: ../examples/tealish_boilerplate.tl
    :language: tealish

Every application requires both an `Approval Program and a Clear State Program <https://developer.algorand.org/docs/get-details/dapps/smart-contracts/apps/#the-lifecycle-of-a-smart-contract>`_.
So far we have only shown the Approval Program. In most cases the Clear State program is extremely simple and just accepts.

.. literalinclude:: ../examples/minimal.tl
    :language: tealish


Build Your App
--------------

.. code-block::

    $ tealish compile approval.tl
    $ tealish compile clear.tl

After compling the Tealish programs, the ``build/`` directory will now contain ``approval.teal`` and ``clear.teal``.


Deploying Your App
------------------

For instructions on deploying the application using the generated Teal files, please refer to the official `Algorand Docs <https://developer.algorand.org/docs/get-details/dapps/smart-contracts/frontend/apps/>`_.