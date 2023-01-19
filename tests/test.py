from pathlib import Path
import unittest
from unittest import expectedFailure
from typing import List

from tealish import (
    reformat_program,
    TealishCompiler,
    TealWriter,
)
from tealish.errors import (
    CompileError,
    ParseError,
)
from tealish.nodes import Node
from tealish.tx_expressions import parse_expression
from tealish.utils import strip_comments
from tealish.scope import Scope
from tealish.tealish_builtins import AVMType


def compile_lines(source_lines: List[str]) -> List[str]:
    compiler = TealishCompiler(source_lines)
    compiler.parse()
    compiler.compile()
    teal_lines = compiler.output
    return teal_lines


def compile_min(p):
    teal = compile_lines(p)
    min_teal = strip_comments(teal)
    return min_teal


def compile_expression_min(p, **kwargs):
    teal = compile_expression(p, **kwargs)
    min_teal = strip_comments(teal)
    return min_teal


def compile_expression(expression, scope=None):
    parent = Node("")
    parent.new_scope()
    parent.current_scope.update(scope or Scope())
    node = parse_expression(expression)
    node.parent = parent
    node.process()
    writer = TealWriter()
    node.write_teal(writer)
    return writer.output


class TestTealVersion(unittest.TestCase):
    def test_one_character(self):
        teal = compile_min(["#pragma version 6"])
        self.assertEqual(teal[0], "#pragma version 6")

    def test_multiple_characters(self):
        teal = compile_min(["#pragma version 12"])
        self.assertEqual(teal[0], "#pragma version 12")

    def test_invalid_version(self):
        with self.assertRaises(ParseError):
            compile_min(["#pragma version a"])


class TestFields(unittest.TestCase):
    def test_txn_array_index_0(self):
        teal = compile_expression_min("Txn.Accounts[0]")
        self.assertEqual(teal, ["txna Accounts 0"])

    def test_txn_array_index_expression(self):
        teal = compile_expression_min("Txn.Accounts[1 + 1]")
        self.assertEqual(teal, ["pushint 1", "pushint 1", "+", "txnas Accounts"])

    def test_group_txn_array_index_0(self):
        teal = compile_expression_min("Gtxn[0].Accounts[0]")
        self.assertEqual(teal, ["gtxna 0 Accounts 0"])

    def test_group_txn_array_index_expression(self):
        teal = compile_expression_min("Gtxn[0].Accounts[1 + 1]")
        self.assertEqual(teal, ["pushint 1", "pushint 1", "+", "gtxnas 0 Accounts"])

    def test_group_txn_index_expression_array_index_expression(self):
        teal = compile_expression_min("Gtxn[1 + 1].Accounts[1 + 1]")
        self.assertEqual(
            teal,
            [
                "pushint 1",
                "pushint 1",
                "+",
                "pushint 1",
                "pushint 1",
                "+",
                "gtxnsas Accounts",
            ],
        )

    def test_group_index_0(self):
        teal = compile_expression_min("Gtxn[0].TypeEnum")
        self.assertEqual(teal, ["gtxn 0 TypeEnum"])

    def test_group_index_1(self):
        teal = compile_expression_min("Gtxn[1].TypeEnum")
        self.assertEqual(teal, ["gtxn 1 TypeEnum"])

    def test_group_index_15(self):
        teal = compile_expression_min("Gtxn[15].TypeEnum")
        self.assertEqual(teal, ["gtxn 15 TypeEnum"])

    def test_group_index_negative(self):
        teal = compile_expression_min("Gtxn[-1].TypeEnum")
        self.assertListEqual(
            teal, ["txn GroupIndex", "pushint 1", "-", "gtxns TypeEnum"]
        )

    def test_group_index_positive(self):
        teal = compile_expression_min("Gtxn[+1].TypeEnum")
        self.assertListEqual(
            teal, ["txn GroupIndex", "pushint 1", "+", "gtxns TypeEnum"]
        )

    def test_group_index_var(self):
        scope = Scope()
        scope.declare_var("index", AVMType.int)
        teal = compile_expression_min("Gtxn[index].TypeEnum", scope=scope)
        self.assertListEqual(teal, ["load 0", "gtxns TypeEnum"])

    def test_group_index_expression(self):
        teal = compile_expression_min("Gtxn[1 + 2].TypeEnum")
        self.assertListEqual(teal, ["pushint 1", "pushint 2", "+", "gtxns TypeEnum"])


class TestIF(unittest.TestCase):
    def test_pass_simple_if(self):
        teal = compile_min(
            [
                "if 1:",
                "exit(0)",
                "end",
            ]
        )
        self.assertListEqual(
            teal, ["pushint 1", "bz l0_end", "pushint 0", "return", "l0_end:"]
        )

    def test_pass_if_not(self):
        teal = compile_min(
            [
                "if not 1:",
                "exit(0)",
                "end",
            ]
        )
        self.assertListEqual(
            teal, ["pushint 1", "bnz l0_end", "pushint 0", "return", "l0_end:"]
        )

    def test_pass_if_else(self):
        teal = compile_min(
            [
                "if 1:",
                "exit(0)",
                "else:",
                "exit(1)",
                "end",
            ]
        )
        self.assertListEqual(
            teal,
            [
                "pushint 1",
                "bz l0_else",
                "pushint 0",
                "return",
                "b l0_end",
                "l0_else:",
                "pushint 1",
                "return",
                "l0_end:",
            ],
        )

    def test_pass_if_elif(self):
        teal = compile_min(
            [
                "if 1:",
                "exit(0)",
                "elif 2:",
                "exit(1)",
                "end",
            ]
        )
        self.assertListEqual(
            teal,
            [
                "pushint 1",
                "bz l0_elif_0",
                "pushint 0",
                "return",
                "b l0_end",
                "l0_elif_0:",
                "pushint 2",
                "bz l0_end",
                "pushint 1",
                "return",
                "l0_end:",
            ],
        )

    def test_pass_if_elif_not(self):
        teal = compile_min(
            [
                "if 1:",
                "exit(0)",
                "elif not 2:",
                "exit(1)",
                "end",
            ]
        )
        self.assertListEqual(
            teal,
            [
                "pushint 1",
                "bz l0_elif_0",
                "pushint 0",
                "return",
                "b l0_end",
                "l0_elif_0:",
                "pushint 2",
                "bnz l0_end",
                "pushint 1",
                "return",
                "l0_end:",
            ],
        )


class TestAssignment(unittest.TestCase):
    def test_assign(self):
        teal = compile_min(["int x = 1"])
        self.assertListEqual(teal, ["pushint 1", "store 0"])

    def test_declare_assign(self):
        teal = compile_min(["int x", "x = 1"])
        self.assertListEqual(teal, ["pushint 1", "store 0"])

    def test_double_assign(self):
        teal = compile_min(
            [
                "int exists",
                "int balance",
                "exists, balance = asset_holding_get(AssetBalance, 0, 123)",
            ]
        )
        self.assertListEqual(
            teal,
            [
                "pushint 0",
                "pushint 123",
                "asset_holding_get AssetBalance",
                "store 0",
                "store 1",
            ],
        )

    def test_fail_assign_without_declare(self):
        with self.assertRaises(CompileError) as e:
            _ = compile_min(["x = 1"])
        self.assertEqual(
            e.exception.args[0],
            'Var "x" not declared in current scope at line 1\n x = 1',
        )

    def test_fail_invalid(self):
        with self.assertRaises(ParseError):
            compile_min(
                ["int balanceexists, balance = asset_holding_get(AssetBalance, 0, 123)"]
            )


class TestAssert(unittest.TestCase):
    def test_pass_assert_with_message(self):
        teal = compile_min(['assert(1, "Error 1")'])
        self.assertListEqual(teal, ["pushint 1", "assert"])

    def test_pass_assert_with_message_collection(self):
        compiler = TealishCompiler(["assert(0)", 'assert(1, "Error 1")'])
        compiler.compile()
        self.assertDictEqual(compiler.error_messages, {2: "Error 1"})

    def test_pass_simple_assert(self):
        teal = compile_min(["assert(1)"])
        self.assertListEqual(teal, ["pushint 1", "assert"])

    def test_pass_assert_with_group_expression(self):
        compile_lines(["assert(1 && (2 >= 1))"])

    def test_pass_1(self):
        teal = compile_min(["int x = balance(0)"])
        self.assertListEqual(teal, ["pushint 0", "balance", "store 0"])

    def test_fail_wrong_type(self):
        with self.assertRaises(CompileError) as e:
            compile_min(['assert("abc")'])
        self.assertIn(
            "Incorrect type for assert. Expected int, got bytes", str(e.exception)
        )


class TestFunctionReturn(unittest.TestCase):
    def test_pass(self):
        compile_lines(
            [
                "func f():",
                "return",
                "end",
            ]
        )

    def test_fail_no_return(self):
        with self.assertRaises(ParseError) as e:
            compile_lines(
                [
                    "func f():",
                    "assert(1)",
                    "end",
                ]
            )
        self.assertIn("func must end with a return statement", e.exception.args[0])

    @expectedFailure
    def test_fail_wrong_sig_1_return(self):
        with self.assertRaises(CompileError) as e:
            compile_lines(
                [
                    "func f():",
                    "return 1",
                    "end",
                ]
            )
        self.assertIn(
            "Function signature and return statement differ", e.exception.args[0]
        )

    @expectedFailure
    def test_fail_wrong_sig_2_returns(self):
        with self.assertRaises(CompileError) as e:
            compile_lines(
                [
                    "func f() int:",
                    "return 1, 2",
                    "end",
                ]
            )
        self.assertIn(
            "Function signature and return statement differ", e.exception.args[0]
        )

    def test_pass_return_literal(self):
        compile_lines(
            [
                "func f() int:",
                "return 1",
                "end",
            ]
        )

    def test_pass_return_two_literals(self):
        compile_lines(
            [
                "func f() int, int:",
                "return 1, 2",
                "end",
            ]
        )

    def test_pass_return_math_expression(self):
        compile_lines(
            [
                "func f() int:",
                "return 1 + 2",
                "end",
            ]
        )

    def test_pass_return_two_math_expressions(self):
        compile_lines(
            [
                "func f() int, int:",
                "return 1 + 2, 3 + 1",
                "end",
            ]
        )

    def test_pass_return_bytes_with_comma(self):
        teal = compile_min(
            [
                "func f() bytes:",
                'return "1,2,3"',
                "end",
            ]
        )
        self.assertListEqual(teal[1:], ['pushbytes "1,2,3"', "retsub"])

    def test_pass_return_two_func_calls(self):
        teal = compile_min(
            [
                "func f() int, int:",
                "return sqrt(25), exp(5, 2)",
                "end",
            ]
        )
        self.assertListEqual(
            teal[1:], ["pushint 5", "pushint 2", "exp", "pushint 25", "sqrt", "retsub"]
        )


class TestTypeCheck(unittest.TestCase):
    def test_debug(self):
        compile_min(
            [
                "assert(2)",
                "assert(1 + 2)",
            ]
        )

    def test_pass_1(self):
        compile_min(
            [
                "assert(1 + 2)",
            ]
        )

    def test_pass_2(self):
        compile_min(["int a = 3", "assert(btoi(itob(1)) + a)"])

    def test_pass_3(self):
        compile_min(["assert(Txn.Sender == Txn.Receiver)"])

    def test_fail_1(self):
        with self.assertRaises(CompileError) as e:
            compile_min(["bytes x = sqrt(25)"])
        self.assertIn(
            "Incorrect type for bytes assignment. Expected bytes, got int",
            str(e.exception),
        )

    def test_fail_2(self):
        with self.assertRaises(CompileError):
            compile_min(['assert(sqrt("abc"))'])

    def test_fail_3(self):
        with self.assertRaises(CompileError):
            compile_min(["assert(itob(1) + 2)"])

    def test_fail_4(self):
        with self.assertRaises(CompileError) as e:
            compile_min(["int x", "x = itob(2)"])
        self.assertIn(
            "Incorrect type for int assignment. Expected int, got bytes",
            str(e.exception),
        )

    def test_fail_5(self):
        with self.assertRaises(CompileError) as e:
            compile_min(["bytes b", "b = 2"])
        self.assertIn(
            "Incorrect type for bytes assignment. Expected bytes, got int",
            str(e.exception),
        )


class TestInnerGroup(unittest.TestCase):
    def test_pass_simple_inner_group(self):
        teal = compile_min(
            [
                "inner_group:",
                "inner_txn:",
                "TypeEnum: Axfer",
                "Fee: 0",
                "AssetReceiver: Txn.Sender",
                "XferAsset: 10",
                "AssetAmount: 2000000",
                "end",
                "inner_txn:",
                "TypeEnum: Appl",
                "Fee: 2000",
                "ApplicationID: 1",
                'ApplicationArgs[0]: "swap"',
                "ApplicationArgs[1]: 30",
                'ApplicationArgs[2]: "fixed-input"',
                "Accounts[0]: Txn.Accounts[1]",
                "Assets[0]: Txn.Assets[0]",
                "Assets[1]: Txn.Assets[1]",
                "end",
                "end",
            ]
        )
        self.assertListEqual(
            teal,
            [
                "itxn_begin",
                "pushint 4",
                "itxn_field TypeEnum",
                "pushint 0",
                "itxn_field Fee",
                "txn Sender",
                "itxn_field AssetReceiver",
                "pushint 10",
                "itxn_field XferAsset",
                "pushint 2000000",
                "itxn_field AssetAmount",
                "itxn_next",
                "pushint 6",
                "itxn_field TypeEnum",
                "pushint 2000",
                "itxn_field Fee",
                "pushint 1",
                "itxn_field ApplicationID",
                'pushbytes "swap"',
                "itxn_field ApplicationArgs",
                "pushint 30",
                "itxn_field ApplicationArgs",
                'pushbytes "fixed-input"',
                "itxn_field ApplicationArgs",
                "txna Accounts 1",
                "itxn_field Accounts",
                "txna Assets 0",
                "itxn_field Assets",
                "txna Assets 1",
                "itxn_field Assets",
                "itxn_submit",
            ],
        )

    @expectedFailure
    def test_pass_inner_group_with_if(self):
        # TODO: This currently fails because we don't correctly
        # figure out which is the first txn of the group
        teal = compile_min(
            [
                "int asset_id",
                "inner_group:",
                "if asset_id:",
                "inner_txn:",
                "TypeEnum: Axfer",
                "Fee: 0",
                "AssetReceiver: Txn.Sender",
                "XferAsset: asset_id",
                "AssetAmount: 2000000",
                "end",
                "else:",
                "inner_txn:",
                "TypeEnum: Pay",
                "Fee: 0",
                "Receiver: Txn.Sender",
                "XferAsset: asset_id",
                "Amount: 2000000",
                "end",
                "end",
                "inner_txn:",
                "TypeEnum: Appl",
                "Fee: 2000",
                "ApplicationID: 1",
                'ApplicationArgs[0]: "swap"',
                "ApplicationArgs[1]: 30",
                'ApplicationArgs[2]: "fixed-input"',
                "Accounts[0]: Txn.Accounts[1]",
                "Assets[0]: Txn.Assets[0]",
                "Assets[1]: Txn.Assets[1]",
                "end",
                "end",
            ]
        )
        self.assertListEqual(
            teal,
            [
                "itxn_begin",
                "load 0",
                "bz l0_else",
                "pushint 4",
                "itxn_field TypeEnum",
                "pushint 0",
                "itxn_field Fee",
                "txn Sender",
                "itxn_field AssetReceiver",
                "load 0",
                "itxn_field XferAsset",
                "pushint 2000000",
                "itxn_field AssetAmount",
                "b l0_end",
                "l0_else:",
                "pushint 1",
                "itxn_field TypeEnum",
                "pushint 0",
                "itxn_field Fee",
                "txn Sender",
                "itxn_field Receiver",
                "load 0",
                "itxn_field XferAsset",
                "pushint 2000000",
                "itxn_field Amount",
                "l0_end:",
                "itxn_next",
                "pushint 6",
                "itxn_field TypeEnum",
                "pushint 2000",
                "itxn_field Fee",
                "pushint 1",
                "itxn_field ApplicationID",
                'pushbytes "swap"',
                "itxn_field ApplicationArgs",
                "pushint 30",
                "itxn_field ApplicationArgs",
                'pushbytes "fixed-input"',
                "itxn_field ApplicationArgs",
                "txna Accounts 1",
                "itxn_field Accounts",
                "txna Assets 0",
                "itxn_field Assets",
                "txna Assets 1",
                "itxn_field Assets",
                "itxn_submit",
            ],
        )

    def test_pass_inner_group_with_statement(self):
        teal = compile_min(
            [
                "int a",
                "int b",
                "inner_group:",
                "int c = a + b",
                "inner_txn:",
                "TypeEnum: Axfer",
                "Fee: 0",
                "AssetReceiver: Txn.Sender",
                "XferAsset: c",
                "AssetAmount: 2000000",
                "end",
                "end",
            ]
        )
        self.assertListEqual(
            teal,
            [
                "itxn_begin",
                "load 0",
                "load 1",
                "+",
                "store 2",
                "pushint 4",
                "itxn_field TypeEnum",
                "pushint 0",
                "itxn_field Fee",
                "txn Sender",
                "itxn_field AssetReceiver",
                "load 2",
                "itxn_field XferAsset",
                "pushint 2000000",
                "itxn_field AssetAmount",
                "itxn_submit",
            ],
        )


class TestOperators(unittest.TestCase):
    def test_binary(self):
        teal = compile_expression_min("1 || 2")
        self.assertEqual(
            teal,
            [
                "pushint 1",
                "pushint 2",
                "||",
            ],
        )

    def test_unary_literal_int(self):
        teal = compile_expression_min("!1")
        self.assertEqual(
            teal,
            [
                "pushint 1",
                "!",
            ],
        )

    def test_unary_literal_bytes(self):
        teal = compile_expression_min('b~"\x00\x00\x00\x00\x00\x00\x00\x00"')
        self.assertEqual(
            teal,
            [
                'pushbytes "\x00\x00\x00\x00\x00\x00\x00\x00"',
                "b~",
            ],
        )

    def test_unary_variable(self):
        scope = Scope()
        scope.declare_var("x", AVMType.int)
        teal = compile_expression_min("!x", scope=scope)
        self.assertEqual(
            teal,
            [
                "load 0",
                "!",
            ],
        )

    def test_unary_functioncall(self):
        teal = compile_expression_min("!sqrt(25)")
        self.assertEqual(
            teal,
            [
                "pushint 25",
                "sqrt",
                "!",
            ],
        )

    def test_unary_group(self):
        teal = compile_expression_min("!(0 || 1)")
        self.assertEqual(
            teal,
            [
                "pushint 0",
                "pushint 1",
                "||",
                "!",
            ],
        )

    def test_binary_with_unary_b(self):
        teal = compile_expression_min("1 || !1")
        self.assertEqual(
            teal,
            [
                "pushint 1",
                "pushint 1",
                "!",
                "||",
            ],
        )

    def test_binary_with_unary_a(self):
        teal = compile_min(["assert(!1 || 1)"])
        teal = compile_expression_min("!1 || 1")
        self.assertEqual(
            teal,
            [
                "pushint 1",
                "!",
                "pushint 1",
                "||",
            ],
        )


class TestWhile(unittest.TestCase):
    def test_pass_simple(self):
        teal = compile_min(
            [
                "int x = 1",
                "while x < 10:",
                "x = x + 1",
                "end",
            ]
        )
        self.assertListEqual(
            teal,
            [
                "pushint 1",
                "store 0",
                "l0_while:",
                "load 0",
                "pushint 10",
                "<",
                "bz l0_end",
                "load 0",
                "pushint 1",
                "+",
                "store 0",
                "b l0_while",
                "l0_end:",
            ],
        )

    def test_pass_while_break(self):
        teal = compile_min(
            [
                "int x = 1",
                "while 1:",
                "x = x + 1",
                "break",
                "end",
            ]
        )
        self.assertListEqual(
            teal,
            [
                "pushint 1",
                "store 0",
                "l0_while:",
                "pushint 1",
                "bz l0_end",
                "load 0",
                "pushint 1",
                "+",
                "store 0",
                "b l0_end",
                "b l0_while",
                "l0_end:",
            ],
        )

    def test_fail_break_outside_while(self):
        with self.assertRaises(ParseError) as e:
            compile_min(
                [
                    "int x = 1",
                    "break",
                ]
            )
        self.assertIn('"break" should only be used in a while loop!', str(e.exception))


class TestForLoop(unittest.TestCase):
    def test_pass_implicit(self):
        teal = compile_min(
            [
                "for _ in 0:10:",
                'log("a")',
                "end",
            ]
        )
        self.assertListEqual(
            teal,
            [
                "pushint 0",
                "dup",
                "l0_for:",
                "pushint 10",
                "==",
                "bnz l0_end",
                'pushbytes "a"',
                "log",
                "pushint 1",
                "+",
                "dup",
                "b l0_for",
                "pop",
                "l0_end:",
            ],
        )

    def test_pass_explicit(self):
        teal = compile_min(
            [
                "for i in 0:10:",
                'log("a")',
                "end",
            ]
        )
        self.assertListEqual(
            teal,
            [
                "pushint 0",
                "store 0",
                "l0_for:",
                "load 0",
                "pushint 10",
                "==",
                "bnz l0_end",
                'pushbytes "a"',
                "log",
                "load 0",
                "pushint 1",
                "+",
                "store 0",
                "b l0_for",
                "l0_end:",
            ],
        )


class TestStructs(unittest.TestCase):
    def test_pass_definition(self):
        teal = compile_min(
            [
                "struct Item:",
                "   a: int",
                "   b: int",
                "   c: bytes[10]",
                "end",
            ]
        )
        self.assertListEqual(teal, [])

    def test_fail_definition_lowercase_name(self):
        with self.assertRaises(ParseError):
            compile_min(
                [
                    "struct item:",
                    "   a: int",
                    "   b: int",
                    "   c: bytes[10]",
                    "end",
                ]
            )

    def test_fail_definition_uppercase_field_name(self):
        with self.assertRaises(ParseError):
            compile_min(
                [
                    "struct Item:",
                    "   A: int",
                    "   b: int",
                    "   c: bytes[10]",
                    "end",
                ]
            )

    def test_fail_definition_after_statement(self):
        with self.assertRaises(ParseError):
            compile_min(
                [
                    "int x = 1",
                    "struct Item:",
                    "   a: int",
                    "   b: int",
                    "   c: bytes[10]",
                    "end",
                ]
            )

    def test_fail_definition_inside_statement(self):
        with self.assertRaises(ParseError):
            compile_min(
                [
                    "if 1:",
                    "   struct Item:",
                    "       a: int",
                    "       b: int",
                    "       c: bytes[10]",
                    "   end",
                    "end",
                ]
            )

    def test_pass_declaration(self):
        teal = compile_min(
            [
                "struct Item:",
                "   a: int",
                "   b: int",
                "   c: bytes[10]",
                "end",
                "Item item1 = Txn.ApplicationArgs[0]",
            ]
        )
        self.assertListEqual(
            teal,
            [
                "txna ApplicationArgs 0",
                "store 0",
            ],
        )

    def test_pass_int_field_access(self):
        teal = compile_min(
            [
                "struct Item:",
                "   a: int",
                "   b: int",
                "   c: bytes[10]",
                "end",
                "Item item1 = Txn.ApplicationArgs[0]",
                "assert(item1.a)",
            ]
        )
        self.assertListEqual(
            teal,
            [
                "txna ApplicationArgs 0",
                "store 0",
                "load 0",
                "pushint 0",
                "extract_uint64",
                "assert",
            ],
        )

    def test_pass_byte_field_access(self):
        teal = compile_min(
            [
                "struct Item:",
                "   a: int",
                "   b: int",
                "   c: bytes[10]",
                "end",
                "Item item1 = Txn.ApplicationArgs[0]",
                "log(item1.c)",
            ]
        )
        self.assertListEqual(
            teal,
            [
                "txna ApplicationArgs 0",
                "store 0",
                "load 0",
                "extract 16 10",
                "log",
            ],
        )

    def test_pass_byte_field_assignment(self):
        teal = compile_min(
            [
                "struct Item:",
                "   a: int",
                "   b: int",
                "   c: bytes[10]",
                "end",
                "Item item1 = bzero(28)",
                "item1.c = Txn.ApplicationArgs[0]",
            ]
        )
        self.assertListEqual(
            teal,
            [
                "pushint 28",
                "bzero",
                "store 0",
                "load 0",
                "txna ApplicationArgs 0",
                "replace 16",
                "store 0",
            ],
        )

    def test_pass_int_field_assignment(self):
        teal = compile_min(
            [
                "struct Item:",
                "   a: int",
                "   b: int",
                "   c: bytes[10]",
                "end",
                "Item item1 = bzero(28)",
                "item1.a = 1",
            ]
        )
        self.assertListEqual(
            teal,
            [
                "pushint 28",
                "bzero",
                "store 0",
                "load 0",
                "pushint 1",
                "itob",
                "replace 0",
                "store 0",
            ],
        )


class TestBoxes(unittest.TestCase):
    def test_pass_create_box(self):
        teal = compile_min(
            [
                "struct Item:",
                "   a: int",
                "   b: int",
                "   c: bytes[10]",
                "end",
                'box<Item> item1 = CreateBox("a")',
            ]
        )
        self.assertListEqual(
            teal,
            [
                'pushbytes "a"',
                "dup",
                "pushint 26",
                "box_create",
                "assert",
                "store 0",
            ],
        )

    def test_pass_open_box(self):
        teal = compile_min(
            [
                "struct Item:",
                "   a: int",
                "   b: int",
                "   c: bytes[10]",
                "end",
                'box<Item> item1 = OpenBox("a")',
            ]
        )
        self.assertListEqual(
            teal,
            [
                'pushbytes "a"',
                "dup",
                "box_len",
                "assert",
                "pushint 26",
                "==",
                "assert",
                "store 0",
            ],
        )

    def test_pass_box(self):
        teal = compile_min(
            [
                "struct Item:",
                "   a: int",
                "   b: int",
                "   c: bytes[10]",
                "end",
                'box<Item> item1 = Box("a")',
            ]
        )
        self.assertListEqual(
            teal,
            [
                'pushbytes "a"',
                "store 0",
            ],
        )

    def test_pass_int_field_access(self):
        teal = compile_min(
            [
                "struct Item:",
                "   a: int",
                "   b: int",
                "   c: bytes[10]",
                "end",
                'box<Item> item1 = Box("a")',
                "assert(item1.a)",
            ]
        )
        self.assertListEqual(
            teal,
            [
                'pushbytes "a"',
                "store 0",
                "load 0",
                "pushint 0",
                "pushint 8",
                "box_extract",
                "btoi",
                "assert",
            ],
        )

    def test_pass_byte_field_access(self):
        teal = compile_min(
            [
                "struct Item:",
                "   a: int",
                "   b: int",
                "   c: bytes[10]",
                "end",
                'box<Item> item1 = Box("a")',
                "log(item1.c)",
            ]
        )
        self.assertListEqual(
            teal,
            [
                'pushbytes "a"',
                "store 0",
                "load 0",
                "pushint 16",
                "pushint 10",
                "box_extract",
                "log",
            ],
        )

    def test_pass_byte_field_assignment(self):
        teal = compile_min(
            [
                "struct Item:",
                "   a: int",
                "   b: int",
                "   c: bytes[10]",
                "end",
                'box<Item> item1 = Box("a")',
                "item1.c = Txn.ApplicationArgs[0]",
            ]
        )
        self.assertListEqual(
            teal,
            [
                'pushbytes "a"',
                "store 0",
                "load 0",
                "pushint 16",
                "txna ApplicationArgs 0",
                "box_replace",
            ],
        )

    def test_pass_int_field_assignment(self):
        teal = compile_min(
            [
                "struct Item:",
                "   a: int",
                "   b: int",
                "   c: bytes[10]",
                "end",
                'box<Item> item1 = Box("a")',
                "item1.a = 1",
            ]
        )
        self.assertListEqual(
            teal,
            [
                'pushbytes "a"',
                "store 0",
                "load 0",
                "pushint 0",
                "pushint 1",
                "itob",
                "box_replace",
            ],
        )


class TestEverythingProgram(unittest.TestCase):
    maxDiff = None

    def setUp(self) -> None:
        tests_dir = Path(__file__).parent
        with open(tests_dir / "everything.tl") as f:
            self.src_lines = f.read().split("\n")

        with open(tests_dir / "everything.teal") as f:
            self.output_lines = f.read().split("\n")

    def test_pass_parse(self):
        compiler = TealishCompiler(self.src_lines)
        compiler.parse()

    def test_pass_compile(self):
        output = compile_lines(self.src_lines)
        self.assertListEqual(output, self.output_lines)

    def test_pass_reformat(self):
        output = reformat_program("\n".join(self.src_lines))
        self.assertListEqual(output.split("\n"), self.src_lines)
