# Tealish


Tealish is designed first and foremost to be a more readable version of Teal. 
The biggest difference between Teal and Tealish is the stack is made implicit in Tealish instead of being explicit as in Teal. 

Readability is achieved by the following:
- Multiple operations on a single line
- Semantic names for scratch slots (variables)
- Aliases for values on stack
- Named constants
- High level language concepts (if/elif/else, loops, switches)
- A simple style convention

Safety Features:
- Readability
- Named scratch slots
- Scoped scratch slots
- Type checking

Any Teal opcode can be used in Tealish in a procedural style. Additionally there is syntactic sugar for some common operations.
When explicit stack manipulation is required raw Teal can be used inline within a Tealish program.

Tealish is a procedural language, executed from top to bottom. Statements can exist inside blocks or at the top level.
The first statement of a program is the entry point of the program. The program can exit on any line.
Execution can jump from one block to another.

Blocks are used to define scopes. Blocks and variables are scoped to the block they are defined in and are available to any nested blocks.

Blocks are not functions:
- they do not take arguments
- they do not have independent stack space
- they are not re-entrant

Blocks start and end with an empty stack.

Functions take arguments from the stack and return results to the stack. Functions do not have access to externally defined scratch variables. They are generally used for reusable 'pure' operations that have no side effects.

Blocks modify the shared scratch space but only temporarily make local modifications to the shared stack.
Functions modify the shared stack but only temporarily make local modifications to the shared scratch space.


Tealish transpiles to Teal rather than compiling directly to AVM bytecode.
The produced Teal is as idomatic and as close to handwritten Teal as possible.
The original source Tealish (including comments) is included as comments in the generated Teal.
The generated Teal is intended to be readable and auditable.
The generated Teal should not be surprising - the Tealish writer should be able to easily imagine the generated Teal.


Tealish is not a general purpose programming language. It is designed specifically for writing contracts for the AVM, optimizing for common patterns. 



## Tealish building blocks

Program

Statements

Blocks
```
block foo:
    # some statements
end

# A block with an inner block
block foo:
    # some statements

    block foobar:
        # some statements
    end
end
```



Expressions

Comments

Assignments
    types
    scope

If Statements
Switch Statements

Jump statement
return statement


Function Calls

Special:
- exit()
- assert()
- error()


Inner Txns

Inline TEAL

Fields
- Global
- Txn
- Gtxn[i]
- Itxn