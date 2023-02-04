.. Tealish documentation master file, created by
   sphinx-quickstart on Wed Nov 16 21:10:38 2022.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

.. rst-class:: barlow-24

Tealish is a readable language for the Algorand Virtual Machine. It enables developers to write TEAL in a procedural style optimized for readability.

.. rst-class:: barlow-16

Install Tealish and start building with a brand new language for Algorand Virtual Machine.

.. rst-class:: block

``pip install tealish``

.. rst-class:: barlow-16

A simple example demonstrating assertions, state, if statements and inner transactions:

.. literalinclude:: ../examples/counter_prize/counter_prize.tl


Tealish transpiles to Teal rather than compiling directly to AVM bytecode. The produced Teal is as close to handwritten idiomatic Teal as possible. The original source Tealish (including comments) is included as comments in the generated Teal. The generated Teal is intended to be readable and auditable. The generated Teal should not be surprising - the Tealish writer should be able to easily imagine the generated Teal.


Tealish is not a general purpose programming language. It is designed specifically for writing contracts for the AVM, optimizing for common patterns.

.. rst-class:: index-page__content-links

* :ref:`quick_start`
* `Presentation <https://youtu.be/R9oKjwSYuXM>`_
* `Community <https://discord.com/channels/491256308461207573/1067861991982649404>`_

Tealish language is built and maintained by the Tinyman core team for the entire Algorand ecosystem.

.. toctree::
   :maxdepth: 2
   :hidden:

   quick_start
   language
   examples
   cli
   recipes
   questions
   zen
