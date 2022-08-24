import importlib.resources
import json
import logging

from textx.metamodel import metamodel_from_file

import tealish
from .tealish_builtins import constants

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

lang_spec = json.loads(importlib.resources.read_text(package=tealish, resource='langspec.json'))
with importlib.resources.path(tealish, 'tealish_expressions.tx') as p:
    tealish_mm = metamodel_from_file(p, use_regexp_group=True, skipws=True, ws=' \t', debug=False)


class ExpressionCompiler:
    constants = constants

    def __init__(self, source, scope={}) -> None:
        self.current_scope = None
        self.output = []
        self.level = 0
        self.set_scope(scope)
        self.lang_spec = lang_spec
        self.ops = {op['Name']: op for op in self.lang_spec['Ops']}
        self.used_functions = set()
        self.nodes = tealish_mm.model_from_str(source)

    def set_scope(self, scope):
        self.functions = scope.get('functions', {})
        self.consts = scope.get('consts', {})
        self.slots = scope.get('slots', {})

    def compile(self, scope=None):
        self.output = []
        if scope is not None:
            self.set_scope(scope)
        self.visit(self.nodes)
        return self.output

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

    def write(self, s=''):
        prefix = '  ' * self.level
        self.output.append(prefix + s)

    def lookup_const(self, name):
        if name not in self.consts:
            raise KeyError(f'Const "{name}" not declared in current scope')
        return self.consts[name]
            
    def visit(self, node):
        name = node.__class__.__name__
        attr = f'handle_{name}'.lower()
        if hasattr(self, attr):
            handler = getattr(self, attr)
            handler(node)
        else:
            raise Exception(f'No handler for type: {name}')

    def handle_functioncall(self, func_call):
        name = func_call.name
        func = None
        try:
            func = self.lookup_func(func_call.name)
        except KeyError:
            pass
        if func:
            return self.handle_user_defined_func_call(func_call, func)
        try:
            func = self.lookup_op(func_call.name)
        except KeyError:
            pass
        if func:
            return self.handle_op_call(func_call, func)
        if func_call.name == 'error':
            self.write(f'err')
        elif func_call.name == 'push':
            for arg in func_call.args:
                self.visit(arg)
            self.write(f'// {func_call.name}')
        elif func_call.name == 'pop':
            parent = func_call.parent.__class__.__name__
            if parent in ('DeclareAssignment', 'SingleAssignment'):
                self.write(f'// {func_call.name}')
            else:
                self.write(f'{func_call.name}')
        else:
            raise Exception(f'Unknown function or opcode "{func_call.name}"')

    def handle_user_defined_func_call(self, func_call, func):
        for arg in func_call.args:
            self.visit(arg)
        self.write(f'callsub {func.label}')

    def handle_op_call(self, func_call, op):
        immediates = func_call.args[:(op['Size'] - 1)]
        num_args = len(op.get('Args', []))
        args = func_call.args[(op['Size'] - 1):]
        if len(args) != num_args:
            raise Exception(f'Expected {num_args} args for {op["Name"]}!')
        for arg in args:
            self.visit(arg)
        for i, x in enumerate(immediates):
            if x.__class__.__name__ == 'Constant':
                immediates[i] = x.name
        immediate_args = ' '.join(map(str, immediates))
        if immediate_args:
            self.write(f'{func_call.name} {immediate_args}')
        else:
            self.write(f'{func_call.name}')

    def handle_exit(self, node):
        self.visit(node.arg)
        self.write(f'return')

    def handle_return(self, node):
        for expr in node.exprs:
            self.visit(expr)
        self.write(f'retsub')

    def handle_variable(self, variable):
        name = variable.name
        slot = self.lookup_var(name)
        self.write(f'load {slot} // {name}')
    
    def handle_constant(self, constant):
        name = constant.name
        # userdefined constants
        type, value = None, None
        try:
            type, value = self.lookup_const(name)
        except KeyError:
            try:
                type, value = self.constants[name]
            except KeyError:
                raise Exception(f'Constant "{name}" not declared in scope')
        if type == 'int':
            self.write(f'pushint {value} // {name}')
        elif type == 'byte':
            self.write(f'pushbytes {value} // {name}')
        else:
            raise Exception('Unexpected const type')

    def handle_math(self, statement):
        self.visit(statement.a)
        self.visit(statement.b)
        self.write(f'{statement.op}')

    def handle_group(self, statement):
        self.visit(statement.math)

    def handle_int(self, node):
        self.write(f'pushint {node}')

    def handle_str(self, node):
        self.write(f'pushbytes "{node}"')

    def handle_txnfield(self, expr):
        self.write(f'txn {expr.field}')

    def handle_txnarrayfield(self, expr):
        self.write(f'txn {expr.field} {expr.arrayIndex}')

    def handle_negativegroupindex(self, expr):
        self.write(f'txn GroupIndex')
        self.write(f'pushint {expr.index}')
        self.write('-')

    def handle_positivegroupindex(self, expr):
        self.write(f'txn GroupIndex')
        self.write(f'pushint {expr.index}')
        self.write('+')

    def handle_grouptxnfield(self, expr):
        if type(expr.index) != int:
            # index is an expression that needs to be evaluated
            self.visit(expr.index)
            self.write(f'gtxns {expr.field}')
        else:
            # index is a constant
            assert expr.index >= 0, 'Group index < 0'
            assert expr.index < 16, 'Group index > 16'
            self.write(f'gtxn {expr.index} {expr.field}')

    def handle_grouptxnarrayfield(self, expr):
        if type(expr.index) != int:
            # index is an expression that needs to be evaluated
            self.visit(expr.index)
            self.write(f'gtxnsa {expr.field} {expr.arrayIndex}')
        else:
            # index is a constant
            assert expr.index >= 0 and expr.index < 16
            self.write(f'gtxna {expr.index} {expr.field} {expr.arrayIndex}')

    def handle_innertxnfield(self, expr):
        self.write(f'itxn {expr.field}')

    def handle_innertxnarrayfield(self, expr):
        self.write(f'itxn {expr.field} {expr.arrayIndex}')

    def handle_globalfield(self, expr):
        self.write(f'global {expr.field}')


def compile_expression(source, scope={}):
    compiler = ExpressionCompiler(source, scope)
    teal = compiler.output
    return teal
