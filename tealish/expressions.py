import re
from typing import List, get_type_hints
from .tealish_expressions import ExpressionCompiler
from .tealish_builtins import constants

LITERAL_INT = r'[0-9]+'
LITERAL_BYTE = r'"(.+)"'
VARIABLE_NAME = r'[a-z_][a-zA-Z0-9_]*'
FIELD_NAME = r'[A-Z][A-Za-z_]+'
ENUM = r'[A-Z][a-zA-Z]+'


class Expression:
    pattern = r''
    def __init__(self, string) -> None:
        self.string = string
        try:
            self.matches = re.match(self.pattern, self.string).groupdict()
            # print(self, self.matches)
        except Exception:
            raise Exception(f'String "{string}" cannot be parsed as {self.__class__.__name__}')

        type_hints = get_type_hints(self.__class__)
        for name, expr_class in type_hints.items():
            if hasattr(expr_class, 'parse'):
                value = expr_class.parse(self.matches[name])
            else:
                value = self.matches[name]
            setattr(self, name, value)

    def __repr__(self):
        return self.__class__.__name__ + str(self.matches)

    @classmethod
    def match(cls, string):
        return re.match(cls.pattern, string) is not None

    @classmethod
    def parse(cls, string):
        return cls(string)

    def teal(self):
        raise NotImplementedError()


class GenericExpression(Expression):
    @classmethod
    def parse(cls, string):
        try:
            expression = ExpressionCompiler(string)
        except Exception as e:
            # print(string)
            # raise e
            raise Exception(f'Cannot parse "{string}" as Expression')
        expr = cls(string)
        expr.expression = expression
        return expr
    
    def teal(self, scope):
        return self.expression.compile(scope)


class Literal(Expression):
    pattern = rf'(?P<value>{LITERAL_BYTE}|{LITERAL_INT}|{ENUM})$'

    @classmethod
    def parse(cls, string):
        for expr in [LiteralInt, LiteralByte, Enum]:
            if expr.match(string):
                return expr.parse(string)
        raise Exception(f'Cannot parse "{string}" as Literal')


class LiteralInt(Expression):
    pattern = rf'(?P<value>{LITERAL_INT})$'
    value: int

    def teal(self):
        return [f'pushint {self.value}']


class Enum(Expression):
    pattern = rf'(?P<value>{ENUM})$'
    value: str

    def teal(self):
        i = constants[self.value][1]
        return [f'pushint {i} // {self.value}']


class LiteralByte(Expression):
    pattern = rf'(?P<value>{LITERAL_BYTE})$'
    value: str

    def teal(self):
        return [f'pushbytes {self.value}']


class FunctionCall(Expression):
    pattern = rf'(?P<name>[a-zA-Z_0-9]+)\((?P<args>.)*\)$'
    name: str
    args: str
    def teal(self):
        return self.args.teal() + [f'{self.name}']

