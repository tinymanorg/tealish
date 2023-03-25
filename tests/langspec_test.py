from tealish import langspec


def test_langspec():
    ls = langspec.packaged_lang_spec
    for op_name, op_spec in ls.ops.items():
        print(op_spec.sig)
