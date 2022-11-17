.. Tealish documentation master file, created by
   sphinx-quickstart on Wed Nov 16 21:10:38 2022.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

Tealish: A readable language for Algorand 
=========================================

Tealish is a readable language for the Algorand Virtual Machine. It enables developers to write TEAL in a procedural style optimized for readability.


Minimal Example
---------------

A simple example demonstrating assertions, state, if statements and inner transactions::

   #pragma version 6

   if Txn.OnCompletion == UpdateApplication:
      assert(Txn.Sender == Global.CreatorAddress)
      exit(1)
   end

   assert(Txn.OnCompletion == NoOp)

   int counter = app_global_get("counter")
   counter = counter + 1
   app_global_put("counter", counter)

   if counter == 10:
      inner_txn:
         TypeEnum: Pay
         Receiver: Txn.Sender
         Amount: 10000000
      end
   elif counter > 10:
      exit(0)
   end

   exit(1)


Installing
----------

``pip install tealish``

Usage
-----
``tealish compile example.tl``


.. toctree::
   :maxdepth: 2
   :caption: Contents:

   language



Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`
