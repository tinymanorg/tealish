from base64 import b64decode

from algosdk.account import address_from_private_key
from algosdk.atomic_transaction_composer import (
    AccountTransactionSigner,
    AtomicTransactionComposer,
    TransactionWithSigner,
)
from algosdk.logic import get_application_address
from algosdk.transaction import (
    ApplicationCreateTxn,
    OnComplete,
    StateSchema,
    SuggestedParams,
)

from util.client import algod_client
from util.config import build_path


def deploy_app(
    txn_signer: AccountTransactionSigner,
    approval_name: str,
    clear_name: str,
    sp: SuggestedParams,
    global_schema: StateSchema,
    local_schema: StateSchema,
) -> tuple[int, str]:
    with open(build_path / approval_name, "r") as approval:
        with open(build_path / clear_name, "r") as clear:
            address = address_from_private_key(txn_signer.private_key)

            atc = AtomicTransactionComposer()
            atc.add_transaction(
                TransactionWithSigner(
                    txn=ApplicationCreateTxn(
                        sender=address,
                        sp=sp,
                        on_complete=OnComplete.NoOpOC.real,
                        approval_program=_compile_program(approval.read()),
                        clear_program=_compile_program(clear.read()),
                        global_schema=global_schema,
                        local_schema=local_schema,
                    ),
                    signer=txn_signer,
                )
            )
            tx_id = atc.execute(algod_client, 5).tx_ids[0]
            app_id = algod_client.pending_transaction_info(tx_id)["application-index"]
            app_address = get_application_address(app_id)

            return app_id, app_address


def _compile_program(source_code: str) -> bytes:
    compile_response = algod_client.compile(source_code)
    return b64decode(compile_response["result"])
