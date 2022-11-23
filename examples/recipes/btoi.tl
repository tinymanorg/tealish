bytes input_as_bytes = Txn.ApplicationArgs[0]
int input_as_int = btoi(input_as_bytes)

# Example: Total sum of all app arguments
int app_args_count = Txn.NumAppArgs
int total = 0

for index in 0:app_args_count:
    total = total + btoi(Txn.ApplicationArgs[index])
end
