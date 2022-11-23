import os
import unittest
from datetime import datetime, timedelta
from unittest.mock import ANY

from algojig import TealishProgram
from algojig import get_suggested_params
from algojig.ledger import JigLedger
from algosdk.account import generate_account
from algosdk.encoding import decode_address
from algosdk.future import transaction
from algosdk.logic import get_application_address

dirname = os.path.dirname(__file__)
approval_program = TealishProgram(os.path.join(dirname, "../auction.tl"))

ZERO_ADDRESS = b"\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00"
APP_GLOBAL_INTS = 7
APP_GLOBAL_BYTES = 2


class AuctionTests(unittest.TestCase):
    maxDiff = None

    @classmethod
    def setUpClass(cls):
        cls.sp = get_suggested_params()
        cls.app_creator_sk, cls.app_creator_address = generate_account()
        cls.seller_sk, cls.seller_address = generate_account()

        cls.now = datetime.now()
        cls.start_time = cls.now + timedelta(days=1)
        cls.end_time = cls.start_time + timedelta(days=1)
        cls.reserve_amount = 10_000_000  # 10 ALGO
        cls.min_bid_increment = 1_000_000  # 1 ALGO

    def setUp(self):
        self.ledger = JigLedger()
        self.ledger.set_account_balance(self.app_creator_address, 1_000_000)
        self.ledger.set_account_balance(self.seller_address, 1_000_000)
        self.nft_id = self.ledger.create_asset(asset_id=1123, params={"total": 1})
        self.ledger.set_account_balance(self.seller_address, 1, self.nft_id)

    def create_app(self):
        app_id = 10
        self.ledger.create_app(
            app_id=app_id,
            approval_program=approval_program,
            creator=self.app_creator_address,
            local_ints=0,
            local_bytes=0,
            global_ints=APP_GLOBAL_INTS,
            global_bytes=APP_GLOBAL_BYTES,
        )
        self.ledger.set_global_state(
            app_id,
            {
                b"bid_account": ZERO_ADDRESS,
                b"end": int(self.end_time.timestamp()),
                b"min_bid_inc": self.min_bid_increment,
                b"nft_id": self.nft_id,
                b"reserve_amount": self.reserve_amount,
                b"seller": decode_address(self.seller_address),
                b"start": int(self.start_time.timestamp()),
            },
        )
        return app_id

    def test_create_app(self):
        txn = transaction.ApplicationCreateTxn(
            sender=self.app_creator_address,
            sp=self.sp,
            on_complete=transaction.OnComplete.NoOpOC,
            approval_program=approval_program.bytecode,
            clear_program=approval_program.bytecode,
            global_schema=transaction.StateSchema(
                num_uints=APP_GLOBAL_INTS, num_byte_slices=APP_GLOBAL_BYTES
            ),
            local_schema=transaction.StateSchema(num_uints=0, num_byte_slices=0),
            extra_pages=0,
            app_args=[
                self.seller_address,
                self.nft_id,
                int(self.start_time.timestamp()),
                int(self.end_time.timestamp()),
                self.reserve_amount,
                self.min_bid_increment,
            ],
            accounts=[self.seller_address],
        )
        stxn = txn.sign(self.app_creator_sk)

        block = self.ledger.eval_transactions(transactions=[stxn])
        block_txns = block[b"txns"]
        self.assertEqual(len(block_txns), 1)
        txn = block_txns[0]

        app_id = txn[b"apid"]
        self.assertIsNotNone(app_id)

        # check delta
        global_delta = txn[b"dt"][b"gd"]
        self.assertDictEqual(
            global_delta,
            {
                b"bid_account": {b"at": 1, b"bs": ZERO_ADDRESS},
                b"end": {b"at": 2, b"ui": int(self.end_time.timestamp())},
                b"min_bid_inc": {b"at": 2, b"ui": self.min_bid_increment},
                b"nft_id": {b"at": 2, b"ui": self.nft_id},
                b"reserve_amount": {b"at": 2, b"ui": self.reserve_amount},
                b"seller": {b"at": 1, b"bs": decode_address(self.seller_address)},
                b"start": {b"at": 2, b"ui": int(self.start_time.timestamp())},
            },
        )

        # check final state
        final_global_state = self.ledger.get_global_state(
            app_id=app_id,
        )
        self.assertDictEqual(
            final_global_state,
            {
                b"bid_account": ZERO_ADDRESS,
                b"end": int(self.end_time.timestamp()),
                b"min_bid_inc": self.min_bid_increment,
                b"nft_id": self.nft_id,
                b"reserve_amount": self.reserve_amount,
                b"seller": decode_address(self.seller_address),
                b"start": int(self.start_time.timestamp()),
            },
        )

    def test_setup(self):
        app_id = self.create_app()
        app_address = get_application_address(app_id)
        self.ledger.set_account_balance(self.seller_address, 1, self.nft_id)

        # Pay
        # Setup
        # Asset Transfer
        txn_group = [
            transaction.PaymentTxn(
                sender=self.seller_address,
                sp=self.sp,
                receiver=app_address,
                amt=300_000,
            ),
            transaction.ApplicationNoOpTxn(
                sender=self.seller_address,
                sp=self.sp,
                index=app_id,
                app_args=["setup"],
                foreign_assets=[self.nft_id],
            ),
            transaction.AssetTransferTxn(
                sender=self.seller_address,
                sp=self.sp,
                receiver=app_address,
                amt=1,
                index=self.nft_id,
            ),
        ]

        txn_group = transaction.assign_group_id(txn_group)
        stxns = [
            txn_group[0].sign(self.seller_sk),
            txn_group[1].sign(self.seller_sk),
            txn_group[2].sign(self.seller_sk),
        ]

        block = self.ledger.eval_transactions(
            transactions=stxns, block_timestamp=int(self.now.timestamp())
        )
        block_txns = block[b"txns"]

        self.assertEqual(len(block_txns), 3)
        app_call_txn = block_txns[1]

        # check delta
        global_delta = app_call_txn[b"dt"].get(b"gd")
        self.assertEqual(global_delta, None)

        # check inner transactions
        inner_transactions = app_call_txn[b"dt"][b"itx"]
        self.assertEqual(len(inner_transactions), 1)
        first_inner_transaction = inner_transactions[0]

        self.assertDictEqual(
            first_inner_transaction[b"txn"],
            {
                b"arcv": decode_address(app_address),
                b"fee": ANY,
                b"fv": ANY,
                b"lv": ANY,
                b"snd": decode_address(app_address),
                b"type": b"axfer",
                b"xaid": self.nft_id,
            },
        )

    def test_on_bid(self):
        app_id = self.create_app()
        app_address = get_application_address(app_id)
        self.ledger.set_account_balance(app_address, 200_000, asset_id=0)  # Algo
        self.ledger.set_account_balance(app_address, 1, asset_id=self.nft_id)

        initial_balances = 10_000_000
        buyer_1_sk, buyer_1_address = generate_account()
        bid_1_amount = 1_000_000
        self.ledger.set_account_balance(buyer_1_address, initial_balances, asset_id=0)

        buyer_2_sk, buyer_2_address = generate_account()
        bid_2_amount = 4_000_000
        self.ledger.set_account_balance(buyer_2_address, initial_balances, asset_id=0)

        # Pay
        # App Call - Bid
        txn_group = [
            transaction.PaymentTxn(
                sender=buyer_1_address,
                sp=self.sp,
                receiver=app_address,
                amt=bid_1_amount,
            ),
            transaction.ApplicationNoOpTxn(
                sender=buyer_1_address,
                sp=self.sp,
                index=app_id,
                app_args=["bid"],
                foreign_assets=[self.nft_id],
            ),
        ]

        txn_group = transaction.assign_group_id(txn_group)
        stxns = [
            txn_group[0].sign(buyer_1_sk),
            txn_group[1].sign(buyer_1_sk),
        ]

        block = self.ledger.eval_transactions(
            transactions=stxns, block_timestamp=int(self.start_time.timestamp())
        )
        block_txns = block[b"txns"]

        self.assertEqual(len(block_txns), 2)
        app_call_txn = block_txns[1]

        # check delta
        global_delta = app_call_txn[b"dt"].get(b"gd")
        self.assertDictEqual(
            global_delta,
            {
                b"bid_account": {b"at": 1, b"bs": decode_address(buyer_1_address)},
                b"bid_amount": {b"at": 2, b"ui": bid_1_amount},
                b"num_bids": {b"at": 2, b"ui": 1},
            },
        )

        # check final state
        final_global_state = self.ledger.get_global_state(
            app_id=app_id,
        )
        self.assertDictEqual(
            final_global_state,
            {
                b"bid_account": decode_address(buyer_1_address),
                b"bid_amount": bid_1_amount,
                b"num_bids": 1,
                b"end": int(self.end_time.timestamp()),
                b"min_bid_inc": self.min_bid_increment,
                b"nft_id": self.nft_id,
                b"reserve_amount": self.reserve_amount,
                b"seller": decode_address(self.seller_address),
                b"start": int(self.start_time.timestamp()),
            },
        )

        # There is no inner transactions
        self.assertEqual(app_call_txn[b"dt"].get(b"itx"), None)

        # Bid 2
        txn_group = [
            transaction.PaymentTxn(
                sender=buyer_2_address,
                sp=self.sp,
                receiver=app_address,
                amt=bid_2_amount,
            ),
            transaction.ApplicationNoOpTxn(
                sender=buyer_2_address,
                sp=self.sp,
                index=app_id,
                app_args=["bid"],
                foreign_assets=[self.nft_id],
                accounts=[buyer_1_address],
            ),
        ]

        txn_group = transaction.assign_group_id(txn_group)
        stxns = [
            txn_group[0].sign(buyer_2_sk),
            txn_group[1].sign(buyer_2_sk),
        ]

        block = self.ledger.eval_transactions(
            transactions=stxns, block_timestamp=int(self.start_time.timestamp())
        )
        block_txns = block[b"txns"]

        self.assertEqual(len(block_txns), 2)
        app_call_txn = block_txns[1]

        # check delta
        global_delta = app_call_txn[b"dt"].get(b"gd")
        self.assertDictEqual(
            global_delta,
            {
                b"bid_account": {b"at": 1, b"bs": decode_address(buyer_2_address)},
                b"bid_amount": {b"at": 2, b"ui": bid_2_amount},
                b"num_bids": {b"at": 2, b"ui": 2},
            },
        )

        # check final state
        final_global_state = self.ledger.get_global_state(
            app_id=app_id,
        )
        self.assertDictEqual(
            final_global_state,
            {
                b"bid_account": decode_address(buyer_2_address),
                b"bid_amount": bid_2_amount,
                b"num_bids": 2,
                b"end": int(self.end_time.timestamp()),
                b"min_bid_inc": self.min_bid_increment,
                b"nft_id": self.nft_id,
                b"reserve_amount": self.reserve_amount,
                b"seller": decode_address(self.seller_address),
                b"start": int(self.start_time.timestamp()),
            },
        )

        # check inner transactions
        inner_transactions = app_call_txn[b"dt"][b"itx"]
        self.assertEqual(len(inner_transactions), 1)
        first_inner_transaction = inner_transactions[0]
        self.assertDictEqual(
            first_inner_transaction[b"txn"],
            {
                b"amt": bid_1_amount - self.sp.min_fee,
                b"fee": ANY,
                b"fv": ANY,
                b"lv": ANY,
                b"rcv": decode_address(buyer_1_address),
                b"snd": decode_address(app_address),
                b"type": b"pay",
            },
        )

        buyer_1_final_balance, is_frozen = self.ledger.get_account_balance(
            buyer_1_address, asset_id=0
        )
        self.assertEqual(buyer_1_final_balance, initial_balances - self.sp.min_fee * 3)

        buyer_2_final_balance, is_frozen = self.ledger.get_account_balance(
            buyer_2_address, asset_id=0
        )
        self.assertEqual(
            buyer_2_final_balance, initial_balances - bid_2_amount - self.sp.min_fee * 2
        )

    def test_on_delete_before_start_time_by_seller(self):
        app_id = self.create_app()

        txn = transaction.ApplicationDeleteTxn(
            sender=self.seller_address,
            sp=self.sp,
            index=app_id,
            foreign_assets=[self.nft_id],
        )

        stxns = [txn.sign(self.seller_sk)]

        block = self.ledger.eval_transactions(
            transactions=stxns, block_timestamp=int(self.now.timestamp())
        )
        block_txns = block[b"txns"]
        # It is successful
        self.assertEqual(len(block_txns), 1)

    def test_on_delete_before_start_time_by_creator(self):
        app_id = self.create_app()

        txn = transaction.ApplicationDeleteTxn(
            sender=self.app_creator_address,
            sp=self.sp,
            index=app_id,
            foreign_assets=[self.nft_id],
        )

        stxns = [txn.sign(self.app_creator_sk)]

        block = self.ledger.eval_transactions(
            transactions=stxns, block_timestamp=int(self.now.timestamp())
        )
        block_txns = block[b"txns"]
        # It is successful
        self.assertEqual(len(block_txns), 1)

    @unittest.skip
    def test_on_delete_during_the_auction(self):
        raise NotImplementedError

    @unittest.skip
    def test_on_delete_after_end_time(self):
        raise NotImplementedError
