# chat.py
import re, ast
from dsl import Primitive, register_learned_primitive, type_of
from learner import OneShotLearner
from memory import ConceptMemory

class ChatBot:
    def __init__(self, max_program_size=4):
        self.memory  = ConceptMemory()
        self.learner = OneShotLearner(max_program_size=max_program_size, top_k=5)

    # ---------- helpers ----------
    def _parse(self, s):
        s = s.strip()
        try:    return ast.literal_eval(s)
        except: return s

    def _register(self, program, input_types, ret_type, name):
        def fn(*args):
            try:    return program.eval(list(args))
            except: return None
        prim = Primitive(name, fn, input_types, ret_type)
        register_learned_primitive(prim)
        self.memory.add(name, program, input_types, ret_type)

    # ---------- main ----------
    def handle(self, text):
        text = text.strip()
        if not text:
            return "Say something (try 'help')."
        low = text.lower()

        if low in ("help", "/help", "?"):
            return self._help()
        if low.startswith(("teach ", "/teach ")):
            return self._teach(text)
        if low.startswith(("apply ", "/apply ")):
            return self._apply(text)
        if low.startswith(("explain ", "/explain ")):
            return self._explain(text)
        if low in ("concepts", "/concepts", "list"):
            return self._list()
        if low in ("exit", "quit", "/exit", "/quit"):
            return "__EXIT__"

        # fallback: try literal or arithmetic
        try:
            v = ast.literal_eval(text)
            return f"Value: {v!r}"
        except Exception:
            pass
        try:
            return f"= {eval(text, {'__builtins__': {}}, {})}"
        except Exception:
            return "I don't understand. Type 'help'."

    def _help(self):
        return (
            "One-Shot Chat Learner — commands:\n"
            "  teach <input> -> <output> [as <name>]   learn a concept from one example\n"
            "  apply <name> <input>                    apply a learned concept\n"
            "  concepts                                list learned concepts\n"
            "  explain <name>                          show the program of a concept\n"
            "  <arithmetic expr>                       evaluate it (e.g. 2*(3+4))\n"
            "\n"
            "Examples:\n"
            '  teach "hello" -> "OLLEH"\n'
            '  apply concept_1 "world"\n'
            '  teach 3 -> 9\n'
            '  teach "abc" -> "CBA"'
        )

    def _teach(self, text):
        body = re.sub(r"^(/teach|teach)\s+", "", text, flags=re.I).strip()
        parts = body.split("->")
        if len(parts) != 2:
            return "Format: teach <input> -> <output> [as <name>]"
        left, right = parts
        name = None
        m = re.search(r"\s+as\s+(\w+)\s*$", right)
        if m:
            name = m.group(1)
            right = right[:m.start()].strip()
        inp = self._parse(left)
        out = self._parse(right)
        inputs = tuple(inp) if isinstance(inp, (list, tuple)) else (inp,)

        programs = self.learner.learn([(inputs, out)])
        if not programs:
            return ("I couldn't find a consistent program. Try a simpler "
                    "example or increase max_program_size.")

        prog = programs[0]
        if name is None:
            name = self.memory.next_name()
        elif name in self.memory.concepts:
            return f"'{name}' already exists."

        input_types = [type_of(v) for v in inputs]
        ret_type    = type_of(out)
        self._register(prog, input_types, ret_type, name)

        msg = f"Learned: {prog}\nSaved as '{name}'."
        if len(programs) > 1:
            alts = ", ".join(str(p) for p in programs[1:3])
            msg += f"\n(Also consistent: {alts})"
        return msg

    def _apply(self, text):
        body = re.sub(r"^(/apply|apply)\s+", "", text, flags=re.I).strip()
        parts = body.split(None, 1)
        if len(parts) != 2:
            return "Format: apply <name> <input>"
        name, raw = parts
        entry = self.memory.get(name)
        if entry is None:
            return f"No concept '{name}'. Type 'concepts'."
        prog, input_types, _ = entry
        inp = self._parse(raw)
        arity = len(input_types)
        if isinstance(inp, (list, tuple)):
            if len(inp) != arity:
                return f"'{name}' expects {arity} inputs, got {len(inp)}."
            env = list(inp)
        else:
            if arity != 1:
                return f"'{name}' expects {arity} inputs (a list)."
            env = [inp]
        try:
            result = prog.eval(env)
        except Exception as e:
            return f"Error: {e}"
        return f"{name}({raw}) = {result!r}"

    def _explain(self, text):
        body = re.sub(r"^(/explain|explain)\s+", "", text, flags=re.I).strip()
        entry = self.memory.get(body)
        if entry is None:
            return f"No concept '{body}'."
        prog, input_types, ret_type = entry
        return f"{body} = {prog}   (arity {len(input_types)}, returns {ret_type.value})"

    def _list(self):
        if not self.memory.concepts:
            return "Nothing learned yet."
        return "Learned concepts:\n" + "\n".join(
            f"  {n}: {p}" for n, (p, _, _) in self.memory.concepts.items())


def main():
    print("=" * 60)
    print(" One-Shot Chat Learner")
    print(" Type 'help' for commands, 'quit' to exit.")
    print("=" * 60)
    bot = ChatBot(max_program_size=4)
    while True:
        try:
            line = input("\nYou: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nBye."); break
        if not line:
            continue
        reply = bot.handle(line)
        if reply == "__EXIT__":
            print("Bot: Bye."); break
        print("Bot:", reply)

if __name__ == "__main__":
    main()