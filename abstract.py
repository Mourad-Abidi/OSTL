# abstract.py
from collections import Counter
from dsl import Primitive, register_primitive, Type, type_of
from program import PrimitiveNode, Variable


def _canonical(sub):
    vars_seen = {}
    def walk(n):
        if isinstance(n, Variable):
            if n.index not in vars_seen:
                vars_seen[n.index] = len(vars_seen)
            return f"x{vars_seen[n.index]}"
        if isinstance(n, PrimitiveNode):
            return f"({n.prim.name} {' '.join(walk(a) for a in n.args)})"
        return repr(n)
    return walk(sub)


def discover(graph, min_occurrences=2, min_size=3):
    counter, first, sources = Counter(), {}, {}

    for name, node in graph.nodes.items():
        for sub in node.program.subtrees(min_size=min_size):
            if sub.size() >= node.program.size():
                continue
            key = _canonical(sub)
            counter[key] += 1
            sources.setdefault(key, set()).add(name)
            if key not in first:
                first[key] = (sub, node)

    invented = []
    for key, cnt in counter.most_common():
        if len(sources[key]) < min_occurrences:
            continue
        sub, parent = first[key]
        if any(getattr(n.prim, "name", "").startswith("abstract_")
               for n in sub.subtrees() if isinstance(n, PrimitiveNode)):
            continue
        fv = sorted(sub.variables())
        if fv != list(range(len(fv))):
            continue

        k = len(fv)
        arg_types = parent.input_types[:k] if len(parent.input_types) >= k else [Type.ANY] * k
        try:
            ret_val = sub.eval(list(parent.examples[0][0])) if parent.examples else None
            ret_type = type_of(ret_val) if ret_val is not None else Type.ANY
        except Exception:
            ret_type = Type.ANY

        name = f"abstract_{len(invented) + 1}"
        while graph.has(name):
            name = f"abstract_{len(invented) + 1}_{cnt}"

        def make_fn(s):
            def fn(*args):
                try: return s.eval(list(args))
                except Exception: return None
            return fn

        prim = Primitive(name, make_fn(sub), arg_types, ret_type)
        register_primitive(prim)
        invented.append((name, sub, sorted(sources[key])))

    return invented