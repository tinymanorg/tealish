from algosdk.account import generate_account
from algosdk.atomic_transaction_composer import (
    AccountTransactionSigner,
    AtomicTransactionComposer,
    TransactionWithSigner,
)
from algosdk.transaction import PaymentTxn

from util.client import algod_client, kmd_client

DEFAULT_KMD_WALLET_NAME = "unencrypted-default-wallet"
DEFAULT_KMD_WALLET_PASSWORD = ""


def create_new_funded_account() -> tuple[str, AccountTransactionSigner]:
    private, address = generate_account()
    transaction_signer = AccountTransactionSigner(private)
    _fund_account(address)

    return address, transaction_signer


def _fund_account(
    receiver_address: str,
    initial_funds=1_000_000_000,
) -> None:
    funding_address, funding_private = _get_funding_account()
    atc = AtomicTransactionComposer()
    atc.add_transaction(
        TransactionWithSigner(
            txn=PaymentTxn(
                sender=funding_address,
                sp=algod_client.suggested_params(),
                receiver=receiver_address,
                amt=initial_funds,
            ),
            signer=AccountTransactionSigner(funding_private),
        )
    )
    atc.execute(algod_client, 5)


def _get_funding_account() -> tuple[str, str]:
    wallets = kmd_client.list_wallets()

    wallet_id = None
    for wallet in wallets:
        if wallet["name"] == DEFAULT_KMD_WALLET_NAME:
            wallet_id = wallet["id"]
            break

    if wallet_id is None:
        raise Exception("Wallet {} not found.".format(DEFAULT_KMD_WALLET_NAME))

    wallet_handle = kmd_client.init_wallet_handle(
        wallet_id, DEFAULT_KMD_WALLET_PASSWORD
    )

    addresses = kmd_client.list_keys(wallet_handle)

    for address in addresses:
        account_info = algod_client.account_info(address)
        if (
            account_info["status"] != "Offline"
            and account_info["amount"] > 1_000_000_000
        ):
            private = kmd_client.export_key(
                wallet_handle, DEFAULT_KMD_WALLET_PASSWORD, address
            )
            return address, private

    raise Exception("Cannot find a funding account.")
