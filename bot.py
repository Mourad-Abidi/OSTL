# bot.py
import re, ast
from dsl import register_primitive, type_of, Primitive, Type, LEARNED_PRIMITIVES
from learner import OneShotLearner
from graph import ConceptGraph
from abstract import discover


class Bot:
    def __init__(self, max_size=4, neural_oracle=None, neural_online=False):
        from dsl import LEARNED_PRIMITIVES  # ← new import
        LEARNED_PRIMITIVES.clear()  # ← new line
        self.graph = ConceptGraph()
        self.learner = OneShotLearner(max_program_size=max_size)
        self._abstract_count = 0
        self.neural_oracle = neural_oracle
        self.neural_online = neural_online

    def _parse(self, s):
        s = s.strip()
        try: return ast.literal_eval(s)
        except Exception: return s

    # ---------- command dispatch ----------
    def handle(self, text):
        text = text.strip()
        if not text: return "?"
        low = text.lower()
        if low in ("help", "/help", "?"):            return self._help()
        if low in ("quit", "exit", "/quit"):         return "__EXIT__"
        if low.startswith(("teach ", "/teach ")):    return self._teach(text)
        if low.startswith(("apply ", "/apply ")):    return self._apply(text)
        if low.startswith(("why ", "/why ")):        return self._why(text)
        if low.startswith(("explain ", "/explain ")): return self._explain(text)
        if low in ("concepts", "/concepts", "list"): return self._list()
        if low in ("invent", "/invent"):             return self._invent()
        try:
            return f"= {eval(text, {'__builtins__': {}}, {})}"
        except Exception:
            return "Try 'help'."

    def _help(self):
        return (
            "One-Shot Concept Learner\n"
            "  teach <input> -> <output> [as <name>]   learn from one example\n"
            "  apply <name> <input>                    apply a concept\n"
            "  why <name> <input>                      show reasoning trace\n"
            "  explain <name>                          show the rule\n"
            "  concepts                                list concepts\n"
            "  invent                                  discover new abstractions\n"
            "  quit\n"
            "Example: teach \"hello\" -> \"OLLEH\""
        )

    # ---------- commands ----------
    def _teach(self, text):
        body = re.sub(r"^(/teach|teach)\s+", "", text, flags=re.I).strip()
        if "->" not in body:
            return "Format: teach <input> -> <output> [as <name>]"
        left, right = body.split("->", 1)
        name = None
        m = re.search(r"\s+as\s+(\w+)\s*$", right)
        if m:
            name = m.group(1)
            right = right[:m.start()].strip()
        inp = self._parse(left)
        out = self._parse(right)
        inputs = tuple(inp) if isinstance(inp, (list, tuple)) else (inp,)

        # 1) Neural proposal (fast path)
        prog, source = None, None
        if self.neural_oracle and len(inputs) == 1:
            try:
                for cand, prob in self.neural_oracle.propose(inputs[0], out, top_k=5):
                    if not cand.variables():
                        continue
                    if cand.eval(list(inputs)) == out:
                        prog, source = cand, "neural"
                        break
            except Exception:
                pass

        # 2) Symbolic search (fallback / verification)
        if prog is None:
            progs = self.learner.learn([(inputs, out)])
            if not progs:
                return "No consistent rule found. Try a simpler example."
            prog, source = progs[0], "search"

        if name is None: name = self.graph.auto_name()
        elif self.graph.has(name): return f"'{name}' exists."

        input_types = [type_of(v) for v in inputs]
        ret_type = type_of(out)
        self.graph.add(name, prog, input_types, ret_type, example=(inputs, out))

        def fn(*args, _p=prog):
            try: return _p.eval(list(args))
            except Exception: return None
        register_primitive(Primitive(name, fn, input_types, ret_type))

        # Online learning: nudge the neural net toward this example
        if self.neural_online and self.neural_oracle and len(inputs) == 1:
            try:
                self.neural_oracle.online_update(inputs[0], out, prog)
            except Exception:
                pass

        msg = f"Learned {prog}  →  '{name}'  [{source}]"
        if len(progs) > 1:
            msg += f"\n(Other consistent rules: {', '.join(map(str, progs[1:3]))})"
        return msg

    def _apply(self, text):
        body = re.sub(r"^(/apply|apply)\s+", "", text, flags=re.I).strip()
        if " " not in body: return "Format: apply <name> <input>"
        name, raw = body.split(None, 1)
        node = self.graph.get(name)
        if node is None: return f"No concept '{name}'."
        inp = self._parse(raw)
        env = list(inp) if isinstance(inp, (list, tuple)) else [inp]
        if len(env) != len(node.input_types):
            return f"'{name}' expects {len(node.input_types)} inputs."
        try:
            result = node.program.eval(env)
        except Exception as e:
            return f"Error: {e}"
        return f"{name}({raw}) = {result!r}"

    def _why(self, text):
        body = re.sub(r"^(/why|why)\s+", "", text, flags=re.I).strip()
        if " " not in body: return "Format: why <name> <input>"
        name, raw = body.split(None, 1)
        node = self.graph.get(name)
        if node is None: return f"No concept '{name}'."
        inp = self._parse(raw)
        env = list(inp) if isinstance(inp, (list, tuple)) else [inp]
        try:
            result, fired = self.graph.evaluate_trace(name, env)
        except Exception as e:
            return f"Error: {e}"
        lines = [f"{name} = {node.program}"]
        if fired:
            lines.append("Sub-concepts fired (in order):")
            for sub, val in fired:
                lines.append(f"  {sub} → {val!r}")
        else:
            lines.append("(no learned sub-concepts used — primitive-only rule)")
        lines.append(f"Result: {result!r}")
        return "\n".join(lines)

    def _explain(self, text):
        body = re.sub(r"^(/explain|explain)\s+", "", text, flags=re.I).strip()
        node = self.graph.get(body)
        if node is None: return f"No concept '{body}'."
        return (f"{body} = {node.program}\n"
                f"  arity {len(node.input_types)}, returns {node.ret_type.value}\n"
                f"  depends on: {node.dependencies}\n"
                f"  used by:    {node.dependents}")

    def _list(self):
        if not self.graph.nodes: return "Nothing learned yet."
        out = ["Concepts (name → rule):"]
        for name, n in self.graph.nodes.items():
            depth = self.graph.depth(name)
            out.append(f"  {'  '*depth}{name} = {n.program}")
        return "\n".join(out)

    def _invent(self):
        if len(self.graph.nodes) < 2:
            return "Need at least 2 concepts before I can invent abstractions."
        invented = discover(self.graph, min_occurrences=2, min_size=3)
        if not invented:
            return "No recurring patterns found yet."
        for name, sub, src in invented:
            if self.graph.has(name):
                continue
            src_node = self.graph.get(src[0]) if src else None
            k = len(sub.variables())
            if src_node and len(src_node.input_types) >= k:
                input_types = list(src_node.input_types[:k])
            else:
                input_types = [Type.ANY] * k
            ret_type = Type.ANY
            if src_node and src_node.examples:
                try:
                    ret_val = sub.eval(list(src_node.examples[0][0]))
                    if ret_val is not None:
                        ret_type = type_of(ret_val)
                except Exception:
                    pass
            self.graph.add(name, sub, input_types, ret_type)
        return "Invented new abstractions:\n" + "\n".join(
            f"  {n} = {s}   (found in: {', '.join(src)})" for n, s, src in invented)

    # ---------- state for GUI ----------
    def state(self):
        g = self.graph
        concepts, edges = [], []
        for name, n in g.nodes.items():
            concepts.append({
                "name": name,
                "program": str(n.program),
                "depth": g.depth(name),
                "isAbstract": name.startswith("abstract"),
                "deps": list(n.dependencies),
                "dependents": list(n.dependents),
                "examples": [
                    {"inputs": list(inp), "output": out}
                    for inp, out in n.examples
                ],
            })
            for d in n.dependencies:
                if d in g.nodes:
                    edges.append([d, name])
        return {
            "concepts": concepts,
            "edges": edges,
            "stats": {
                "total": len(concepts),
                "abstract": sum(1 for c in concepts if c["isAbstract"]),
                "maxDepth": max((c["depth"] for c in concepts), default=0),
            },
        }

    # ---------- persistence ----------
    def export_state(self):
        g = self.graph
        return {
            "version": 1,
            "concepts": [
                {
                    "name": name,
                    "program": n.program.to_dict(),
                    "input_types": [t.value for t in n.input_types],
                    "ret_type": n.ret_type.value,
                    "examples": [
                        {"inputs": list(inp), "output": out}
                        for inp, out in n.examples
                    ],
                }
                for name, n in g.nodes.items()
            ],
        }

    def import_state(self, data):
        from program import program_from_dict

        LEARNED_PRIMITIVES.clear()
        self.graph = ConceptGraph()
        self._abstract_count = 0
        max_auto = 0

        for c in data.get("concepts", []):
            prog = program_from_dict(c["program"])
            input_types = [Type(v) for v in c["input_types"]]
            ret_type = Type(c["ret_type"])
            examples = [(tuple(e["inputs"]), e["output"]) for e in c.get("examples", [])]
            self.graph.add(c["name"], prog, input_types, ret_type,
                           example=examples[0] if examples else None)

            def fn(*args, _p=prog):
                try: return _p.eval(list(args))
                except Exception: return None
            register_primitive(Primitive(c["name"], fn, input_types, ret_type))

            m = re.match(r"concept_(\d+)$", c["name"])
            if m:
                max_auto = max(max_auto, int(m.group(1)))
        self.graph._auto = max_auto
        return len(data.get("concepts", []))

