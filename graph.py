# graph.py
class ConceptNode:
    def __init__(self, name, program, input_types, ret_type, example=None):
        self.name = name
        self.program = program
        self.input_types = input_types
        self.ret_type = ret_type
        self.examples = [example] if example else []
        self.dependencies = self._deps(program)   # primitives it calls
        self.dependents = []                      # concepts that call it

    def _deps(self, prog):
        out = set()
        def visit(n):
            from program import PrimitiveNode
            if isinstance(n, PrimitiveNode):
                out.add(n.prim.name)
                for a in n.args: visit(a)
        visit(prog)
        return list(out)

class ConceptGraph:
    """A semantic network of concepts. Replaces the flat dict."""
    def __init__(self):
        self.nodes = {}
        self._auto = 0

    def auto_name(self):
        self._auto += 1
        return f"concept_{self._auto}"

    def add(self, name, program, input_types, ret_type, example=None):
        node = ConceptNode(name, program, input_types, ret_type, example)
        self.nodes[name] = node
        for d in node.dependencies:
            if d in self.nodes:
                self.nodes[d].dependents.append(name)
        return node

    def has(self, name): return name in self.nodes
    def get(self, name): return self.nodes.get(name)

    def transitive_ancestors(self, name):
        """Every concept that (transitively) uses `name`."""
        seen, stack = set(), [name]
        while stack:
            cur = stack.pop()
            if cur in self.nodes:
                for d in self.nodes[cur].dependents:
                    if d not in seen:
                        seen.add(d); stack.append(d)
        return seen

    def depth(self, name, _seen=None):
        """Longest chain of dependencies — how 'deep' the concept is."""
        _seen = _seen or set()
        if name in _seen or name not in self.nodes: return 0
        _seen.add(name)
        deps = [d for d in self.nodes[name].dependencies if d in self.nodes]
        if not deps: return 0
        return 1 + max(self.depth(d, set(_seen)) for d in deps)

    def evaluate_trace(self, name, env):
        """Apply the concept and record which sub-concepts fire."""
        node = self.nodes[name]
        fired = []
        def walk(prog, env):
            from program import PrimitiveNode
            if isinstance(prog, PrimitiveNode):
                val = prog.eval(env)
                if prog.prim.name in self.nodes:
                    fired.append((prog.prim.name, val))
                for a in prog.args:
                    walk(a, env)
        walk(node.program, env)
        return node.program.eval(env), fired