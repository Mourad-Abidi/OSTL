# program.py
from dsl import all_primitives


class Node:
    def eval(self, env): raise NotImplementedError
    def size(self): raise NotImplementedError
    def variables(self):
        out = set()
        def visit(n):
            if isinstance(n, Variable): out.add(n.index)
            elif isinstance(n, PrimitiveNode):
                for a in n.args: visit(a)
        visit(self); return out
    def subtrees(self, min_size=1):
        out = [self] if self.size() >= min_size else []
        if isinstance(self, PrimitiveNode):
            for a in self.args:
                out.extend(a.subtrees(min_size))
        return out
    def to_dict(self): raise NotImplementedError


class Constant(Node):
    def __init__(self, v): self.value = v
    def eval(self, env): return self.value
    def size(self): return 1
    def __repr__(self): return repr(self.value)
    def to_dict(self): return {"t": "c", "v": self.value}


class Variable(Node):
    def __init__(self, i): self.index = i
    def eval(self, env): return env[self.index] if self.index < len(env) else None
    def size(self): return 1
    def __repr__(self): return f"x{self.index}"
    def to_dict(self): return {"t": "x", "i": self.index}


class PrimitiveNode(Node):
    def __init__(self, prim, args):
        self.prim = prim; self.args = args
    def eval(self, env):
        vals = [a.eval(env) for a in self.args]
        if any(v is None for v in vals): return None
        return self.prim(*vals)
    def size(self): return 1 + sum(a.size() for a in self.args)
    def __repr__(self): return f"({self.prim.name} {' '.join(map(str, self.args))})"
    def to_dict(self):
        return {"t": "p", "n": self.prim.name, "a": [x.to_dict() for x in self.args]}


def program_from_dict(d):
    t = d["t"]
    if t == "c": return Constant(d["v"])
    if t == "x": return Variable(d["i"])
    if t == "p":
        prim = next((p for p in all_primitives() if p.name == d["n"]), None)
        if prim is None:
            raise ValueError(f"Unknown primitive: {d['n']}")
        return PrimitiveNode(prim, [program_from_dict(a) for a in d["a"]])
    raise ValueError(f"Unknown node type: {t}")