from itertools import product
from dsl import all_primitives, type_of, base_constants, Type
from program import Constant, Variable, PrimitiveNode


def _splits(total, parts):
    if parts == 1: return [(total,)]
    out = []
    for i in range(1, total - parts + 2):
        for rest in _splits(total - i, parts - 1):
            out.append((i,) + rest)
    return out


def _consts(examples):
    """Constants allowed in search.

    KEY FIX: exclude any value that appears in the example input/output.
    Rationale — the single-example setting is fundamentally ambiguous:
        3 -> 9  matches  (* 3 x0),  (* x0 3),  (* x0 x0),  (** x0 2)
    The first two *memorise* the input as a constant. They are the
    inductive equivalent of cheating. The correct generalisation uses
    the variable. Excluding example values forces the search to prefer
    variable-based programs, which is exactly the Bayesian prior we want.
    """
    example_vals = set()
    for inp, out in examples:
        for v in list(inp) + [out]:
            if isinstance(v, (int, float, bool, str)):
                example_vals.add(v)
    return [c for c in base_constants() if c not in example_vals]


def _num_constants(prog):
    """Count Constant leaves — fewer is more general."""
    return sum(1 for n in prog.subtrees() if isinstance(n, Constant))


def _program_cost(prog):
    """MDL cost: (size, num_constants). Lower is better.

    Two programs of equal size are ranked by how many arbitrary
    constants they contain. 0-constant programs are the most general.
    """
    return (prog.size(), _num_constants(prog))


class OneShotLearner:
    def __init__(self, max_program_size=4, top_k=5):
        self.max_size = max_program_size
        self.top_k = top_k

    def learn(self, examples):
        input_types = [type_of(v) for v in examples[0][0]]
        consts = _consts(examples)
        for size in range(1, self.max_size + 1):
            fits = self._search(examples, input_types, consts, size)
            if fits:
                fits.sort(key=_program_cost)          # ← MDL prior
                return fits[:self.top_k]
        return []

    def _search(self, examples, input_types, consts, max_size):
        bucket = [dict() for _ in range(max_size + 1)]
        bucket[1] = {}
        for c in consts:                               # deterministically ordered
            bucket[1].setdefault(type_of(c), []).append(Constant(c))
        for i, t in enumerate(input_types):
            bucket[1].setdefault(t, []).append(Variable(i))

        for size in range(2, max_size + 1):
            bucket[size] = {}
            for prim in all_primitives():
                if size - 1 < prim.arity: continue
                for split in _splits(size - 1, prim.arity):
                    lists, ok = [], True
                    for s, t in zip(split, prim.arg_types):
                        if t == Type.ANY:
                            cands = [p for l in bucket[s].values() for p in l]
                        else:
                            cands = list(bucket[s].get(t, [])) + \
                                    list(bucket[s].get(Type.ANY, []))
                        if not cands: ok = False; break
                        lists.append(cands)
                    if not ok: continue
                    for args in product(*lists):
                        bucket[size].setdefault(prim.ret_type, []).append(
                            PrimitiveNode(prim, list(args)))

        target_types = {type_of(out) for _, out in examples}
        fits = []
        for size in range(1, max_size + 1):
            for t, lst in bucket[size].items():
                if t != Type.ANY and t not in target_types: continue
                for prog in lst:
                    if not prog.variables(): continue
                    if all(self._eval(prog, inp) == out for inp, out in examples):
                        fits.append(prog)
        return fits

    def _eval(self, prog, inp):
        try: return prog.eval(list(inp))
        except Exception: return object()