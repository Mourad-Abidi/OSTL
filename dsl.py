# dsl.py
from enum import Enum

class Type(Enum):
    NUM = "num"; STR = "str"; BOOL = "bool"; LIST = "list"; ANY = "any"

class Primitive:
    def __init__(self, name, func, arg_types, ret_type):
        self.name = name; self.func = func
        self.arg_types = arg_types; self.ret_type = ret_type
        self.arity = len(arg_types)
    def __call__(self, *args):
        try: return self.func(*args)
        except Exception: return None
    def __repr__(self): return self.name

def _num(n, op):
    def f(a, b):
        if isinstance(a, bool) or isinstance(b, bool): return None
        if isinstance(a, (int, float)) and isinstance(b, (int, float)): return op(a, b)
        return None
    return Primitive(n, f, [Type.NUM, Type.NUM], Type.NUM)

def _cmp(n, op):
    def f(a, b):
        if isinstance(a, (int, float)) and isinstance(b, (int, float)): return op(a, b)
        return None
    return Primitive(n, f, [Type.NUM, Type.NUM], Type.BOOL)

def _str1(n, fn):
    def f(s): return fn(s) if isinstance(s, str) else None
    return Primitive(n, f, [Type.STR], Type.STR)

BASE_PRIMITIVES = [
    _num("+", lambda a, b: a + b), _num("-", lambda a, b: a - b),
    _num("*", lambda a, b: a * b),
    _num("**", lambda a, b: a ** b if isinstance(b, int) and 0 <= b < 10 else None),
    _cmp(">", lambda a, b: a > b), _cmp("<", lambda a, b: a < b),
    _str1("upper", str.upper), _str1("lower", str.lower),
    _str1("reverse", lambda s: s[::-1]),
]

LEARNED_PRIMITIVES = []

def all_primitives(): return BASE_PRIMITIVES + LEARNED_PRIMITIVES
def register_primitive(p): LEARNED_PRIMITIVES.append(p)

def type_of(v):
    if isinstance(v, bool): return Type.BOOL
    if isinstance(v, (int, float)): return Type.NUM
    if isinstance(v, str): return Type.STR
    if isinstance(v, list): return Type.LIST
    return Type.ANY

def base_constants(): return [0, 1, 2, 3, 10, True, False, "", "a"]