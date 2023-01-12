import os
import unittest

from algojig import TealishProgram
from algojig import get_suggested_params
from algojig.ledger import JigLedger
from algosdk.account import generate_account
from algosdk.future import transaction

dirname = os.path.dirname(__file__)
approval_program = TealishProgram(os.path.join(dirname, "../counter_prize.tl"))


class TestCreateApp(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.sp = get_suggested_params()
        cls.app_creator_sk, cls.app_creator_address = generate_account()
        cls.user_sk, cls.user_address = generate_account()

    def setUp(self):
        self.ledger = JigLedger()
        self.ledger.set_account_balance(self.app_creator_address, 1_000_000)
        self.ledger.set_account_balance(self.user_address, 1_000_000)

    def test_create_app(self):
        txn = transaction.ApplicationCreateTxn(
            sender=self.app_creator_address,
            sp=self.sp,
            on_complete=transaction.OnComplete.NoOpOC,
            approval_program=approval_program.bytecode,
            clear_program=approval_program.bytecode,
            global_schema=transaction.StateSchema(num_uints=1, num_byte_slices=0),
            local_schema=transaction.StateSchema(num_uints=0, num_byte_slices=0),
            extra_pages=0,
        )
        stxn = txn.sign(self.app_creator_sk)

        block = self.ledger.eval_transactions(transactions=[stxn])
        block_txns = block[b"txns"]

        self.assertEqual(len(block_txns), 1)
        txn = block_txns[0]

        app_id = txn[b"apid"]
        self.assertIsNotNone(app_id)

        # check final state
        final_global_state = self.ledger.get_global_state(
            app_id=app_id,
        )
        self.assertDictEqual(
            final_global_state,
            {b"counter": 0},
        )

        # check delta
        global_delta = txn[b"dt"][b"gd"]
        self.assertDictEqual(
            global_delta,
            {b"counter": {b"at": 2}},
        )

    def test_counter(self):
        app_id = 10
        self.ledger.create_app(
            app_id=app_id,
            approval_program=approval_program,
            creator=self.app_creator_address,
            local_ints=0,
            local_bytes=0,
            global_ints=1,
            global_bytes=0,
        )
        self.ledger.set_global_state(
            app_id,
            {
                b"counter": 0,
            },
        )

        for new_counter_value in range(1, 5):
            txn = transaction.ApplicationNoOpTxn(
                sender=self.user_address,
                sp=self.sp,
                index=app_id,
            )
            stxn = txn.sign(self.user_sk)

            block = self.ledger.eval_transactions(transactions=[stxn])
            block_txns = block[b"txns"]

            self.assertEqual(len(block_txns), 1)
            txn = block_txns[0]

            # check final state
            final_global_state = self.ledger.get_global_state(
                app_id=app_id,
            )
            self.assertDictEqual(
                final_global_state,
                {b"counter": new_counter_value},
            )

            # check delta
            global_delta = txn[b"dt"][b"gd"]
            self.assertDictEqual(
                global_delta,
                {b"counter": {b"at": 2, b"ui": new_counter_value}},
            )
