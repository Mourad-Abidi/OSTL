#!/usr/bin/env python3
"""
OSTL test suite. Run:  python test_ostl.py
Copy the output back for analysis.
"""
import sys, time, traceback, json

from bot import Bot
from dsl import type_of

PASS, FAIL, INFO, ERR = "PASS", "FAIL", "INFO", "ERR"
results = []


def log(cat, name, status, detail=""):
    results.append((cat, name, status, detail))
    icon = {"PASS": "[PASS]", "FAIL": "[FAIL]", "INFO": "[INFO]", "ERR": "[ERR]"}[status]
    print(f"  {icon} {name}: {detail}")


def section(title):
    print(f"\n{'='*70}\n  {title}\n{'='*70}")


def check(cond, msg):
    if not cond:
        raise AssertionError(msg)


# ────────────────────────────────────────────────────────
# A. Basic symbolic learning
# ────────────────────────────────────────────────────────
def test_basic():
    section("A. Basic symbolic learning")
    bot = Bot(max_size=4)

    reply = bot.handle("teach 3 -> 9")
    log("A", "A1 teach 3 -> 9", PASS if "Learned" in reply else FAIL,
        reply.replace("\n", " | ")[:120])
    c = bot.graph.get("concept_1")
    check(c is not None, "concept_1 not created")
    check(c.program.eval([3]) == 9, f"{c.program} != 9 on input 3")
    log("A", "A1b program verifies", PASS, f"program = {c.program}")

    reply = bot.handle("apply concept_1 7")
    ok = "49" in reply
    log("A", "A2 apply concept_1 7", PASS if ok else FAIL, reply[:100])

    reply = bot.handle('teach "hello" -> "OLLEH"')
    log("A", "A3 teach string", PASS if "Learned" in reply else FAIL,
        reply.replace("\n", " | ")[:120])
    c2 = bot.graph.get("concept_2")
    check(c2 is not None, "concept_2 not created")
    check(c2.program.eval(["abc"]) == "CBA", f"{c2.program} wrong on 'abc'")
    log("A", "A3b program verifies", PASS, f"program = {c2.program}")

    reply = bot.handle("teach 5 -> 25")
    c3 = bot.graph.get("concept_3")
    reused = c3 and any(d.startswith("concept_") for d in c3.dependencies)
    log("A", "A4 teach 5 -> 25", INFO,
        reply.replace("\n", " | ")[:150])
    log("A", "A4b reuse occurred", PASS if reused else INFO,
        f"concept_3 = {c3.program}" if c3 else "no concept_3")

    reply = bot.handle("teach 5 -> 5")
    log("A", "A5 teach 5 -> 5 (identity)", INFO, reply.replace("\n", " | ")[:100])

    return bot


# ────────────────────────────────────────────────────────
# B. Graph structure
# ────────────────────────────────────────────────────────
def test_graph(bot):
    section("B. Graph structure")
    for name in bot.graph.nodes:
        log("B", f"B1 depth({name})", INFO, str(bot.graph.depth(name)))

    if bot.graph.get("concept_1"):
        log("B", "B2 concept_1 dependents", INFO,
            str(bot.graph.get("concept_1").dependents))

    if bot.graph.get("concept_3"):
        node = bot.graph.get("concept_3")
        log("B", "B3 concept_3 dependencies", INFO, str(node.dependencies))
        try:
            result, fired = bot.graph.evaluate_trace("concept_3", [5])
            log("B", "B4 trace concept_3 on 5", INFO,
                f"result={result}, fired={fired}")
        except Exception as e:
            log("B", "B4 trace failed", ERR, str(e))


# ────────────────────────────────────────────────────────
# C. Persistence
# ────────────────────────────────────────────────────────
def test_persistence(bot):
    section("C. Persistence (export/import)")
    try:
        state = bot.export_state()
        n = len(state["concepts"])
        log("C", "C1 export", PASS if n > 0 else FAIL, f"{n} concepts")
        blob = json.dumps(state)
        log("C", "C2 serializable", PASS, f"{len(blob)} bytes")

        bot2 = Bot(max_size=4)
        count = bot2.import_state(json.loads(blob))
        check(count == n, f"count mismatch {count} vs {n}")
        log("C", "C3 import", PASS, f"{count} concepts restored")

        if bot2.graph.get("concept_1"):
            r = bot2.graph.get("concept_1").program.eval([3])
            log("C", "C4 imported concept evaluates", PASS if r == 9 else FAIL,
                f"concept_1(3) = {r}")
    except Exception as e:
        log("C", "C-persistence", ERR, str(e))
        traceback.print_exc()


# ────────────────────────────────────────────────────────
# D. Invention (direct unit test + attempt via teaching)
# ────────────────────────────────────────────────────────
def test_invention():
    section("D. Invention")
    from graph import ConceptGraph
    from abstract import discover
    from dsl import all_primitives, Type
    from program import PrimitiveNode, Variable, Constant

    # D1 — unit test: two hand-built programs with a shared subtree
    prims = {p.name: p for p in all_primitives()}
    v0 = Variable(0)
    sq = PrimitiveNode(prims["*"], [v0, v0])       # (* x0 x0)  size 3
    p1 = PrimitiveNode(prims["+"], [sq, Constant(1)])   # (+ (* x0 x0) 1)
    p2 = PrimitiveNode(prims["*"], [sq, Constant(2)])   # (* (* x0 x0) 2)

    g = ConceptGraph()
    g.add("c1", p1, [Type.NUM], Type.NUM)
    g.add("c2", p2, [Type.NUM], Type.NUM)

    try:
        invented = discover(g, min_occurrences=2, min_size=3)
        names = [n for n, _, _ in invented]
        log("D", "D1 discover shared subtree",
            PASS if names else FAIL,
            f"invented={names}, subtrees={[str(s) for _, s, _ in invented]}")
    except Exception as e:
        log("D", "D1 discover", ERR, str(e))
        traceback.print_exc()

    # D2 — attempt via teaching (single-example is inherently linear-biased)
    bot = Bot(max_size=5)
    t = time.time()
    for cmd in ["teach 4 -> 17 as A", "teach 5 -> 27 as B"]:
        t0 = time.time()
        reply = bot.handle(cmd)
        log("D", f"D2 {cmd}", INFO,
            f"{time.time()-t0:.1f}s → {reply.replace(chr(10), ' | ')[:100]}")
    log("D", "D3 total teach time", INFO, f"{time.time()-t:.1f}s")
    log("D", "D4 concepts", INFO, str(list(bot.graph.nodes.keys())))

    reply = bot.handle("invent")
    log("D", "D5 invent", INFO, reply.replace("\n", " | ")[:200])
    if "abstract" in reply.lower():
        log("D", "D6 abstraction invented via teaching", PASS, "")
    else:
        log("D", "D6 no abstraction via teaching (may need richer DSL)", INFO, "")


# ────────────────────────────────────────────────────────
# E. Neural oracle
# ────────────────────────────────────────────────────────
def test_neural():
    section("E. Neural oracle")
    try:
        import torch
        log("E", "E1 torch available", PASS, f"v{torch.__version__}")
    except ImportError:
        log("E", "E1 torch missing", INFO, "skipping neural tests")
        return

    from neural import train_oracle, NeuralOracle
    t = time.time()
    oracle = train_oracle(max_size=2, samples_per_program=15, epochs=15)
    if oracle is None:
        log("E", "E2 train", FAIL, "returned None")
        return
    log("E", "E2 train", PASS, f"{time.time()-t:.1f}s")
    log("E", "E3 vocabulary", INFO, str(len(oracle.programs)))

    progs = oracle.propose(3, 9, top_k=5)
    log("E", "E4 propose 3 -> 9", INFO,
        ", ".join(f"{p}({pr:.2f})" for p, pr in progs[:3]))

    fits = [p for p, _ in progs if p.variables() and p.eval([3]) == 9]
    log("E", "E5 valid proposal in top-5",
        PASS if fits else INFO, str([str(p) for p in fits[:2]]))

    try:
        import torch as T
        before = [p.clone() for p in oracle.model.parameters()]
        target = fits[0] if fits else progs[0][0]
        oracle.online_update(3, 9, target)
        after = [p.clone() for p in oracle.model.parameters()]
        delta = sum((a - b).abs().sum().item() for a, b in zip(before, after))
        log("E", "E6 online_update changes weights",
            PASS if delta > 1e-6 else FAIL, f"Δ={delta:.6f}")
    except Exception as e:
        log("E", "E6 online_update", ERR, str(e))

    try:
        oracle.save("/tmp/ostl_oracle.pt")
        o2 = NeuralOracle.load("/tmp/ostl_oracle.pt")
        progs2 = o2.propose(3, 9, top_k=3)
        log("E", "E7 save/load roundtrip", PASS if progs2 else FAIL,
            str(progs2[0][0]) if progs2 else "none")
    except Exception as e:
        log("E", "E7 save/load", ERR, str(e))


# ────────────────────────────────────────────────────────
# F. Edge cases
# ────────────────────────────────────────────────────────
def test_edges():
    section("F. Edge cases & DSL limits")
    bot = Bot(max_size=4)

    reply = bot.handle("teach 5 -> 5")
    ok = "Learned" in reply and "x0" in reply
    log("F", "F1 identity 5 -> 5", PASS if ok else INFO,
        reply.replace("\n", " | ")[:100])

    reply = bot.handle("teach True -> False")
    log("F", "F2 teach True -> False (no 'not' primitive)", INFO, reply[:100])

    reply = bot.handle("teach [2, 3] -> 5")
    log("F", "F3 teach [2,3] -> 5 (multi-input)", INFO,
        reply.replace("\n", " | ")[:120])

    reply = bot.handle('teach "abc" -> "a b c"')
    log("F", "F4 intercalate (no primitive)", INFO, reply[:100])

    reply = bot.handle("teach 7 -> 1029")
    log("F", "F5 hard formula 7 -> 1029", INFO, reply[:100])

    reply = bot.handle("")
    log("F", "F6 empty input", INFO, reply[:50])

    reply = bot.handle("teach nothing")
    log("F", "F7 malformed teach", PASS if "Format" in reply else INFO, reply[:80])

    reply = bot.handle("teach [1, 2, 3] -> 6")
    log("F", "F8 list sum (no len/list prims)", INFO,
        reply.replace("\n", " | ")[:100])


# ────────────────────────────────────────────────────────
# G. Performance
# ────────────────────────────────────────────────────────
def test_performance():
    section("G. Performance")
    for size in [3, 4]:
        bot = Bot(max_size=size)
        t = time.time()
        bot.handle("teach 3 -> 9")
        log("G", f"G1 teach 3->9 max_size={size}", INFO,
            f"{time.time()-t:.2f}s")

    bot = Bot(max_size=5)
    t = time.time()
    bot.handle("teach 4 -> 17")
    log("G", "G2 teach 4->17 max_size=5", INFO, f"{time.time()-t:.2f}s")


# ────────────────────────────────────────────────────────
# Main
# ────────────────────────────────────────────────────────
def main():
    print("\n" + "█" * 70)
    print("█  OSTL TEST SUITE")
    print("█" * 70)

    bot = test_basic()
    test_graph(bot)
    test_persistence(bot)
    test_edges()
    test_performance()
    test_invention()
    test_neural()

    print("\n" + "█" * 70)
    print("█  SUMMARY")
    print("█" * 70)
    counts = {PASS: 0, FAIL: 0, INFO: 0, ERR: 0}
    for _, _, st, _ in results:
        counts[st] += 1
    print(f"  Total: {len(results)}  |  PASS: {counts[PASS]}  "
          f"FAIL: {counts[FAIL]}  ERR: {counts[ERR]}  INFO: {counts[INFO]}")

    bad = [r for r in results if r[2] in (FAIL, ERR)]
    if bad:
        print("\n  Problems:")
        for cat, name, st, detail in bad:
            print(f"    [{st}] {name}: {detail}")

    print("\n" + "█" * 70)
    print("█  MACHINE-READABLE RESULTS (paste this back)")
    print("█" * 70)
    for cat, name, st, detail in results:
        print(f"{cat}|{name}|{st}|{detail}")


if __name__ == "__main__":
    main()