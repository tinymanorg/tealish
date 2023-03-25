.. Tealish documentation master file, created by
   sphinx-quickstart on Wed Nov 16 21:10:38 2022.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

.. title:: Tealish by Tinyman


.. rst-class:: barlow-24

Tealish is a readable language for the `Algorand Virtual Machine (AVM) <https://developer.algorand.org/docs/get-details/dapps/avm/teal/specification/>`_. It enables developers to write `Teal <https://developer.algorand.org/docs/get-details/dapps/avm/teal/>`_ in a procedural style optimized for readability.

.. rst-class:: barlow-16

Install Tealish and start building with a brand new language designed for the AVM.

.. rst-class:: block

``pip install tealish``

.. rst-class:: barlow-16

A simple example demonstrating the use of assertions, state, if statements, and inner transactions:

.. literalinclude:: ../examples/counter_prize/counter_prize.tl
   :language: tealish


Tealish transpiles code to Teal, rather than directly compiling to AVM bytecode. The produced Teal is as close to handwritten idiomatic Teal as possible. The original Tealish source code, including comments, is included as comments in the generated Teal code. The generated Teal code is designed to be easily readable and auditable, and should not contain any surprises - Tealish writers should be able to easily understand the generated Teal code.

.. The example below shows the generated Teal for the Tealish program above.

.. .. literalinclude:: ../examples/counter_prize/build/counter_prize.teal
..    :language: teal


You can view the generated Teal code for the example above `here <https://github.com/tinymanorg/tealish/blob/main/examples/counter_prize/build/counter_prize.teal>`_.

Tealish is not intended to be a general-purpose programming language. Instead, it is specifically designed for writing contracts for the AVM, with a focus on optimizing common patterns.

.. rst-class:: index-page__content-links

* :ref:`quick_start`
* `Presentation <https://youtu.be/R9oKjwSYuXM>`_
* `Community <https://discord.com/channels/491256308461207573/1067861991982649404>`_

The Tealish language is built and maintained by the `Tinyman <https://tinyman.org>`_ core team for the benefit of the entire Algorand ecosystem.

.. toctree::
   :maxdepth: 2
   :hidden:

   quick_start
   language
   avm
   examples
   cli
   recipes
   questions
   usage
   zen
