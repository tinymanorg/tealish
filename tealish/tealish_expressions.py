import importlib.resources
import json
import logging

from textx.metamodel import metamodel_from_file

import tealish
from .tealish_builtins import constants
from .expression_nodes import class_provider

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

lang_spec = json.loads(importlib.resources.read_text(package=tealish, resource='langspec.json'))
with importlib.resources.path(tealish, 'tealish_expressions.tx') as p:
    tealish_mm = metamodel_from_file(
        p,
        use_regexp_group=True,
        skipws=True,
        ws=' \t',
        debug=False,
        classes=class_provider,
    )


def type_lookup(a):
    return {
        '.': 'any',
        'B': 'bytes',
        'U': 'int',
        '': 'None',
    }[a]


class ExpressionCompiler:
    constants = constants

    def __init__(self, source, scope={}) -> None:
        self.current_scope = None
        self.output = []
        self.set_scope(scope)
        self.lang_spec = lang_spec
        self.ops = {op['Name']: op for op in self.lang_spec['Ops']}
        self.txn_fields = dict(zip(self.ops['txn']['ArgEnum'], map(type_lookup, self.ops['txn']['ArgEnumTypes'])))
        self.global_fields = dict(zip(self.ops['global']['ArgEnum'], map(type_lookup, self.ops['global']['ArgEnumTypes'])))
        self.used_functions = set()
        self.node = tealish_mm.model_from_str(source)

    def set_scope(self, scope):
        self.functions = scope.get('functions', {})
        self.consts = scope.get('consts', {})
        self.slots = scope.get('slots', {})

    def process(self, scope=None):
        if scope is not None:
            self.set_scope(scope)
        if hasattr(self.node, 'process'):
            self.node.process(self)

    def teal(self):
        return self.node.teal()

    def check_arg_types(self, name, args):
        op = self.lookup_op(name)
        arg_types = [type_lookup(x) for x in op.get('Args', '')]
        for i, arg in enumerate(args):
            if arg.type != 'any' and arg_types[i] != 'any' and arg.type != arg_types[i]:
                raise Exception(f'Incorrect type {arg.type} for arg {i} of {name}. Expected {arg_types[i]}')

    def get_field_type(self, namespace, name):
        if 'txn' in namespace:
            return self.txn_fields[name]
        elif namespace == 'global':
            return self.global_fields[name]

    def lookup_op(self, name):
        if name not in self.ops:
            raise KeyError(f'Op "{name}" does not exist!')
        return self.ops[name]

    def lookup_func(self, name):
        if name not in self.functions:
            raise KeyError(f'Func "{name}" not declared in current scope')
        self.used_functions.add(name)
        return self.functions[name]

    def lookup_var(self, name):
        if name not in self.slots:
            raise KeyError(f'Var "{name}" not declared in current scope')
        return self.slots[name]

    def lookup_const(self, name):
        if name not in self.consts:
            raise KeyError(f'Const "{name}" not declared in current scope')
        return self.consts[name]


def compile_expression(source, scope={}):
    compiler = ExpressionCompiler(source, scope)
    compiler.process(scope)
    teal = compiler.teal()
    return teal
