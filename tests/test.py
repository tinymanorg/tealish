import unittest

import tealish
from tealish import ParseError, compile_lines, minify_teal, TealishCompiler


def compile_min(p):
    teal = compile_lines(p)
    min_teal, _ = minify_teal(teal)
    # remove 'pragma' line
    output = min_teal[1:]
    return output


class TestFields(unittest.TestCase):

    def test_txn_array_index_0(self):
        teal = compile_min([
            'assert(Txn.Accounts[0])'
        ])
        self.assertEqual(teal[0], 'txna Accounts 0')

    def test_txn_array_index_expression(self):
        teal = compile_min([
            'assert(Txn.Accounts[1 + 1])'
        ])
        self.assertEqual(teal[:-1], ['pushint 1', 'pushint 1', '+', 'txnas Accounts'])

    def test_group_txn_array_index_0(self):
        teal = compile_min([
            'assert(Gtxn[0].Accounts[0])'
        ])
        self.assertEqual(teal[:-1], ['gtxna 0 Accounts 0'])

    def test_group_txn_array_index_expression(self):
        teal = compile_min([
            'assert(Gtxn[0].Accounts[1 + 1])'
        ])
        self.assertEqual(teal[:-1], ['pushint 1', 'pushint 1', '+', 'gtxnas 0 Accounts'])

    def test_group_txn_index_expression_array_index_expression(self):
        teal = compile_min([
            'assert(Gtxn[1 + 1].Accounts[1 + 1])'
        ])
        self.assertEqual(teal[:-1], ['pushint 1', 'pushint 1', '+', 'pushint 1', 'pushint 1', '+', 'gtxnsas Accounts'])

    def test_group_index_0(self):
        teal = compile_min([
            'assert(Gtxn[0].TypeEnum)'
        ])
        self.assertEqual(teal[0], 'gtxn 0 TypeEnum')

    def test_group_index_1(self):
        teal = compile_min([
            'assert(Gtxn[1].TypeEnum)'
        ])
        self.assertEqual(teal[0], 'gtxn 1 TypeEnum')

    def test_group_index_15(self):
        teal = compile_min([
            'assert(Gtxn[15].TypeEnum)'
        ])
        self.assertEqual(teal[0], 'gtxn 15 TypeEnum')

    def test_group_index_negative(self):
        teal = compile_min([
            'assert(Gtxn[-1].TypeEnum)'
        ])
        self.assertListEqual(teal[:-1], ['txn GroupIndex', 'pushint 1', '-', 'gtxns TypeEnum'])

    def test_group_index_positive(self):
        teal = compile_min([
            'assert(Gtxn[+1].TypeEnum)'
        ])
        self.assertListEqual(teal[:-1], ['txn GroupIndex', 'pushint 1', '+', 'gtxns TypeEnum'])

    def test_group_index_var(self):
        teal = compile_min([
            'int index = 1',
            'assert(Gtxn[index].TypeEnum)'
        ])
        self.assertListEqual(teal[-3:-1], ['load 0 // index', 'gtxns TypeEnum'])

    def test_group_index_expression(self):
        teal = compile_min([
            'assert(Gtxn[1 + 2].TypeEnum)'
        ])
        self.assertListEqual(teal[:-1], ['pushint 1', 'pushint 2', '+', 'gtxns TypeEnum'])


class TestIF(unittest.TestCase):

    def test_pass_simple_if(self):
        teal = compile_min([
            'if 1:',
            'exit(0)',
            'end',
        ])
        self.assertListEqual(teal, ['pushint 1', 'bz l0_end', 
                                    'pushint 0', 'return', 
                                    'l0_end: // end'])

    def test_pass_if_not(self):
        teal = compile_min([
            'if not 1:',
            'exit(0)',
            'end',
        ])
        self.assertListEqual(teal, ['pushint 1', 'bnz l0_end', 
                                    'pushint 0', 'return', 
                                    'l0_end: // end'])

    def test_pass_if_else(self):
        teal = compile_min([
            'if 1:',
            'exit(0)',
            'else:',
            'exit(1)',
            'end',
        ])
        self.assertListEqual(teal, ['pushint 1', 'bz l0_else', 
                                    'pushint 0', 'return', 'b l0_end',
                                    'l0_else:', 'pushint 1', 'return', 
                                    'l0_end: // end'])

    def test_pass_if_elif(self):
        teal = compile_min([
            'if 1:',
            'exit(0)',
            'elif 2:',
            'exit(1)',
            'end',
        ])
        self.assertListEqual(teal, ['pushint 1', 'bz l0_elif_0', 
                                    'pushint 0', 'return', 'b l0_end',
                                    'l0_elif_0:', 'pushint 2', 'bz l0_end',
                                    'pushint 1', 'return', 
                                    'l0_end: // end'])


    def test_pass_if_elif_not(self):
        teal = compile_min([
            'if 1:',
            'exit(0)',
            'elif not 2:',
            'exit(1)',
            'end',
        ])
        self.assertListEqual(teal, ['pushint 1', 'bz l0_elif_0', 
                                    'pushint 0', 'return', 'b l0_end',
                                    'l0_elif_0:', 'pushint 2', 'bnz l0_end',
                                    'pushint 1', 'return', 
                                    'l0_end: // end'])


class TestAssignment(unittest.TestCase):

    def test_assign(self):
        teal = compile_min([
            'int x = 1'
        ])
        self.assertListEqual(teal, ['pushint 1', 'store 0 // x'])

    def test_declare_assign(self):
        teal = compile_min([
            'int x',
            'x = 1'
        ])
        self.assertListEqual(teal, ['pushint 1', 'store 0 // x'])

    def test_double_assign(self):
        teal = compile_min([
            'int exists',
            'int balance',
            'exists, balance = asset_holding_get(AssetBalance, 0, 123)'
        ])
        self.assertListEqual(teal, ['pushint 0', 'pushint 123', 'asset_holding_get AssetBalance', 'store 0 // exists', 'store 1 // balance'])

    def test_fail_assign_without_declare(self):
        with self.assertRaises(tealish.CompileError) as e:
            teal = compile_min([
                'x = 1'
            ])
            print(teal)
        self.assertEqual(e.exception.args[0], 'Var "x" not declared in current scope at line 1')

    def test_fail_invalid(self):
        with self.assertRaises(Exception):
            teal = compile_min([
                'int balanceexists, balance = asset_holding_get(AssetBalance, 0, 123)'
            ])


class TestAssert(unittest.TestCase):

    def test_pass_assert_with_message(self):
        teal = compile_lines(['assert(1, "Error 1")'])
        self.assertListEqual(teal[2:], ['pushint 1', 'assert // Error 1'])

    def test_pass_assert_with_message_collection(self):
        compiler = TealishCompiler(['assert(0)', 'assert(1, "Error 1")'])
        teal = compiler.compile()
        self.assertDictEqual(compiler.error_messages, {2: 'Error 1'})

    def test_pass_simple_assert(self):
        teal = compile_lines(['assert(1)'])
        self.assertListEqual(teal[2:], ['pushint 1', 'assert'])

    def test_pass_assert_with_group_expression(self):
        teal = compile_lines(['assert(1 && (2 >= 1))'])

    def test_pass_1(self):
        teal = compile_lines(['int x = balance(0)'])
        self.assertListEqual(teal[2:], ['pushint 0', 'balance', 'store 0 // x'])


class TestFunctionReturn(unittest.TestCase):

    def test_pass(self):
        teal = compile_lines([
            'func f():',
            'return',
            'end',
        ])

    def test_fail_no_return(self):
        with self.assertRaises(ParseError) as e:
            compile_lines([
                'func f():',
                'assert(1)',
                'end',
            ])
        self.assertIn('func must end with a return statement', e.exception.args[0])

    def test_pass_return_literal(self):
        teal = compile_lines([
            'func f() int:',
            'return 1',
            'end',
        ])

    def test_pass_return_two_literals(self):
        teal = compile_lines([
            'func f() int, int:',
            'return 1, 2',
            'end',
        ])

    def test_pass_return_math_expression(self):
        teal = compile_lines([
            'func f() int:',
            'return 1 + 2',
            'end',
        ])

    def test_pass_return_two_math_expressions(self):
        teal = compile_lines([
            'func f() int, int:',
            'return 1 + 2, 3 + 1',
            'end',
        ])

    def test_pass_return_bytes_with_comma(self):
        teal = compile_min([
            'func f() byte:',
            'return "1,2,3"',
            'end',
        ])
        self.assertListEqual(teal[1:], ['pushbytes "1,2,3"', 'retsub'])

    def test_pass_return_two_func_calls(self):
        teal = compile_min([
            'func f() int, int:',
            'return sqrt(25), exp(5, 2)',
            'end',
        ])
        self.assertListEqual(teal[1:], ['pushint 5', 'pushint 2', 'exp', 'pushint 25', 'sqrt', 'retsub'])


class TestTypeCheck(unittest.TestCase):

    def test_debug(self):
        teal = compile_min([
            'assert(2)',
            'assert(1 + 2)',
            'assert(itob(1))',
        ])

    def test_pass_1(self):
        teal = compile_min([
        'assert(1 + 2)',
        ])

    def test_pass_2(self):
        teal = compile_min([
        'int a = 3',
        'assert(btoi(itob(1)) + a)'
        ])

    def test_pass_3(self):
        teal = compile_min([
        'assert(Txn.Sender == Txn.Receiver)'
        ])

    def test_fail_1(self):
        with self.assertRaises(Exception) as e:
            teal = compile_min([
                'byte x = sqrt(25)'
            ])
        self.assertIn('Incorrect type for byte assignment. Expected byte, got int', str(e.exception))

    def test_fail_2(self):
        with self.assertRaises(Exception):
            teal = compile_min([
                'assert(sqrt("abc"))'
            ])

    def test_fail_3(self):
        with self.assertRaises(Exception):
            teal = compile_min([
                'assert(itob(1) + 2)'
            ])

    def test_fail_4(self):
        with self.assertRaises(Exception) as e:
            teal = compile_min([
                'int x',
                'x = itob(2)'
            ])
        self.assertIn('Incorrect type for int assignment. Expected int, got byte', str(e.exception))

    def test_fail_5(self):
        with self.assertRaises(Exception) as e:
            teal = compile_min([
                'byte b',
                'b = 2'
            ])
        self.assertIn('Incorrect type for byte assignment. Expected byte, got int', str(e.exception))


class TestInnerGroup(unittest.TestCase):

    def test_pass_simple_inner_group(self):
        teal = compile_min([
            'inner_group:',

            'inner_txn:',
            'TypeEnum: Axfer',
            'Fee: 0',
            'AssetReceiver: Txn.Sender',
            'XferAsset: 10',
            'AssetAmount: 2000000',
            'end',

            'inner_txn:',
            'TypeEnum: Appl',
            'Fee: 2000',
            'ApplicationID: 1',
            'ApplicationArgs[0]: "swap"',
            'ApplicationArgs[1]: 30',
            'ApplicationArgs[2]: "fixed-input"',
            'Accounts[0]: Txn.Accounts[1]',
            'Assets[0]: Txn.Assets[0]',
            'Assets[1]: Txn.Assets[1]',
            'end',

            'end',
        ])
        self.assertListEqual(
            teal,
            [
                'itxn_begin',
                'pushint 4 // Axfer',
                'itxn_field TypeEnum',
                'pushint 0',
                'itxn_field Fee',
                'txn Sender',
                'itxn_field AssetReceiver',
                'pushint 10',
                'itxn_field XferAsset',
                'pushint 2000000',
                'itxn_field AssetAmount',
                'itxn_next',
                'pushint 6 // Appl',
                'itxn_field TypeEnum',
                'pushint 2000',
                'itxn_field Fee',
                'pushint 1',
                'itxn_field ApplicationID',
                'pushbytes "swap"',
                'itxn_field ApplicationArgs',
                'pushint 30',
                'itxn_field ApplicationArgs',
                'pushbytes "fixed-input"',
                'itxn_field ApplicationArgs',
                'txna Accounts 1',
                'itxn_field Accounts',
                'txna Assets 0',
                'itxn_field Assets',
                'txna Assets 1',
                'itxn_field Assets',
                'itxn_submit'
            ]
        )

    def test_pass_inner_group_with_if(self):
        teal = compile_min([
            'int asset_id',
            'inner_group:',
            'if asset_id:',

            'inner_txn:',
            'TypeEnum: Axfer',
            'Fee: 0',
            'AssetReceiver: Txn.Sender',
            'XferAsset: asset_id',
            'AssetAmount: 2000000',
            'end',

            'else:',

            'inner_txn:',
            'TypeEnum: Pay',
            'Fee: 0',
            'Receiver: Txn.Sender',
            'XferAsset: asset_id',
            'Amount: 2000000',
            'end',

            'end',

            'inner_txn:',
            'TypeEnum: Appl',
            'Fee: 2000',
            'ApplicationID: 1',
            'ApplicationArgs[0]: "swap"',
            'ApplicationArgs[1]: 30',
            'ApplicationArgs[2]: "fixed-input"',
            'Accounts[0]: Txn.Accounts[1]',
            'Assets[0]: Txn.Assets[0]',
            'Assets[1]: Txn.Assets[1]',
            'end',

            'end',
        ])
        self.assertListEqual(
            teal,
            [
                'itxn_begin',
                'load 0 // asset_id',
                'bz l0_else',
                'pushint 4 // Axfer',
                'itxn_field TypeEnum',
                'pushint 0',
                'itxn_field Fee',
                'txn Sender',
                'itxn_field AssetReceiver',
                'load 0 // asset_id',
                'itxn_field XferAsset',
                'pushint 2000000',
                'itxn_field AssetAmount',
                'b l0_end',
                'l0_else:',
                'pushint 1 // Pay',
                'itxn_field TypeEnum',
                'pushint 0',
                'itxn_field Fee',
                'txn Sender',
                'itxn_field Receiver',
                'load 0 // asset_id',
                'itxn_field XferAsset',
                'pushint 2000000',
                'itxn_field Amount',
                'l0_end: // end',
                'itxn_next',
                'pushint 6 // Appl',
                'itxn_field TypeEnum',
                'pushint 2000',
                'itxn_field Fee',
                'pushint 1',
                'itxn_field ApplicationID',
                'pushbytes "swap"',
                'itxn_field ApplicationArgs',
                'pushint 30',
                'itxn_field ApplicationArgs',
                'pushbytes "fixed-input"',
                'itxn_field ApplicationArgs',
                'txna Accounts 1',
                'itxn_field Accounts',
                'txna Assets 0',
                'itxn_field Assets',
                'txna Assets 1',
                'itxn_field Assets',
                'itxn_submit'
            ]
        )

    def test_pass_inner_group_with_statement(self):
        teal = compile_min([
            'int a',
            'int b',
            'inner_group:',
            'int c = a + b',
            'inner_txn:',
            'TypeEnum: Axfer',
            'Fee: 0',
            'AssetReceiver: Txn.Sender',
            'XferAsset: c',
            'AssetAmount: 2000000',
            'end',
            'end',
        ])
        self.assertListEqual(
            teal,
            [
                'itxn_begin',
                'load 0 // a',
                'load 1 // b',
                '+',
                'store 2 // c',
                'pushint 4 // Axfer',
                'itxn_field TypeEnum',
                'pushint 0',
                'itxn_field Fee',
                'txn Sender',
                'itxn_field AssetReceiver',
                'load 2 // c',
                'itxn_field XferAsset',
                'pushint 2000000',
                'itxn_field AssetAmount',
                'itxn_submit'
            ]
        )
