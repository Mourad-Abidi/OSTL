# search.py
from typing import Any, List, Tuple, Optional
from dsl import PRIMITIVES
from program import Node, Constant, Variable, PrimitiveNode

def enumerate_programs(max_size: int, num_vars: int) -> List[Node]:
    """Yield all programs up to a given AST size (number of nodes)."""
    # Base cases: constants (small integer/string constants) and variables
    base_nodes = []
    for v in range(num_vars):
        base_nodes.append(Variable(v))
    # A small set of constants (you can expand)
    for c in [0, 1, 2, 3, 5, 10, True, False, "", "a"]:
        base_nodes.append(Constant(c))

    # We'll build programs level by level (BFS over size)
    programs_by_size: List[List[Node]] = [[] for _ in range(max_size + 1)]
    for node in base_nodes:
        programs_by_size[1].append(node)

    for size in range(2, max_size + 1):
        # Build larger programs by combining smaller ones with primitives
        for prim in PRIMITIVES:
            arity = prim.arity
            # Generate all ways to split (size - 1) among `arity` arguments
            # Each argument must have size >= 1
            if size - 1 < arity:  # not enough nodes for this primitive
                continue
            # Recursive generation of argument size tuples
            def gen_splits(total: int, parts: int) -> List[Tuple[int, ...]]:
                if parts == 1:
                    return [(total,)]
                splits = []
                for i in range(1, total - parts + 2):
                    for rest in gen_splits(total - i, parts - 1):
                        splits.append((i,) + rest)
                return splits

            for split in gen_splits(size - 1, arity):
                # Cartesian product of subprograms of those sizes
                from itertools import product
                subprogram_lists = [programs_by_size[s] for s in split]
                for args in product(*subprogram_lists):
                    node = PrimitiveNode(prim, list(args))
                    programs_by_size[size].append(node)

    # Flatten
    all_programs = []
    for s in range(1, max_size + 1):
        all_programs.extend(programs_by_size[s])
    return all_programs

def search_fitting_programs(
    examples: List[Tuple[Any, Any]],
    max_size: int = 6,
    num_vars: int = 1,
    top_k: int = 5
) -> List[Node]:
    """
    Return up to `top_k` shortest programs that exactly fit all examples.
    The search is breadth-first over program size, so the first solutions
    found are the shortest (Occam's razor).
    """
    candidates = enumerate_programs(max_size, num_vars)
    fitting = []
    for prog in candidates:
        ok = True
        for inp, out in examples:
            # Normalize input to a list (environment)
            env = inp if isinstance(inp, (list, tuple)) else [inp]
            try:
                pred = prog.eval(list(env))
            except Exception:
                pred = None
            if pred != out:
                ok = False
                break
        if ok:
            fitting.append(prog)
            if len(fitting) >= top_k:
                break
    # Sort by size (already mostly sorted, but ensure)
    fitting.sort(key=lambda p: p.size())
    return fitting[:top_k]