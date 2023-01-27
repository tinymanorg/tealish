import os
import unittest

from algojig import TealishProgram
from algojig.ledger import JigLedger
from algojig.algod import JigAlgod
from algosdk.account import generate_account
from algosdk.logic import get_application_address
from algosdk.atomic_transaction_composer import (
    AtomicTransactionComposer,
    AccountTransactionSigner,
)

from utils import extract_methods

dirname = os.path.dirname(__file__)
approval_program = TealishProgram(os.path.join(dirname, "app.tl"))


class TestApp(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app_creator_sk, cls.app_creator_address = generate_account()
        cls.user_sk, cls.user_address = generate_account()

    def setUp(self):
        self.app_id = 1
        self.app_address = get_application_address(self.app_id)
        self.ledger = JigLedger()
        self.ledger.set_account_balance(self.user_address, 1_000_000)
        self.ledger.set_account_balance(self.app_address, 10_000_000)
        self.ledger.create_app(app_id=self.app_id, approval_program=approval_program)

    def call_method(self, method_name, args, fee=None, **extra):
        methods = {
            m.name: m for m in extract_methods(approval_program.tealish_source_lines)
        }
        algod = JigAlgod(self.ledger)
        atc = AtomicTransactionComposer()
        signer = AccountTransactionSigner(self.user_sk)
        sp = algod.get_suggested_params()
        if fee:
            sp.fee = fee
        atc.add_method_call(
            method=methods[method_name],
            sender=self.user_address,
            signer=signer,
            sp=sp,
            method_args=args,
            app_id=self.app_id,
            **extra,
        )
        atc.gather_signatures()
        result = atc.execute(algod, 1)
        return result.abi_results[0].return_value

    def test_add(self):
        result = self.call_method("add", [500, 12])
        self.assertEqual(result, 512)

    def test_mulw(self):
        result = self.call_method("mulw", [(2**64 - 1), 1000])
        self.assertEqual(result, (2**64 - 1) * 1000)

    def test_hello(self):
        result = self.call_method("hello", ["world"])
        self.assertEqual(result, "Hello world")

    def test_send(self):
        result = self.call_method("send", [self.user_address], fee=2000)
        self.assertEqual(result, None)

    def test_store_data(self):
        key = b"my_key".zfill(10)
        data = b"some_data".ljust(100, b" ")
        result = self.call_method(
            method_name="store_data",
            args=[key, data],
            boxes=[(0, key)],
        )
        self.assertEqual(result, None)

    def test_store_tuple(self):
        key = b"my_key".zfill(10)
        data = (42, self.user_address, b"some_data".ljust(100, b" "))
        result = self.call_method(
            method_name="store_tuple",
            args=[key, data],
            boxes=[(0, key)],
        )
        self.assertEqual(result, None)

    def test_balance(self):
        result = self.call_method("balance", [self.app_address])
        self.assertEqual(result, 10_000_000)
