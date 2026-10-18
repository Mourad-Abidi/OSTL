<div align="center">

# ◆ OSTL

**One-Shot Concept Learner**

Learn a general rule, formula, or concept from a **single example** — then apply it instantly, compose it, invent new abstractions from it, and get smarter over time.

[![Python](https://img.shields.io/badge/python-3.10%2B-3776AB?style=flat-square&logo=python&logoColor=white)](https://www.python.org/)
[![License](https://img.shields.io/badge/license-MIT-22c55e?style=flat-square)](LICENSE)
[![Dependencies](https://img.shields.io/badge/deps-stdlib%20%2B%20optional%20torch-f59e0b?style=flat-square)](requirements.txt)
[![Status](https://img.shields.io/badge/status-research%20prototype-4f8cff?style=flat-square)]()

[Overview](#overview) · [Quick start](#quick-start) · [How it works](#how-it-works) · [Architecture](#architecture) · [Commands](#commands) · [Enhancing](#enhancing-ostl) · [Contributing](#contributing)

</div>

---

## Overview

OSTL is a **program-induction engine** with a chat interface. You give it one demonstration — `"hello" → "OLLEH"` — and it:

1. **Infers the general rule** as a program in a small DSL: `(upper (reverse x0))`
2. **Applies it to new inputs** immediately: `"world" → "DLROW"`
3. **Composes it** into future concepts: the next teach becomes `(concept_1 x0)`
4. **Invents new abstractions** when it notices recurring patterns across concepts
5. **Accelerates** every future inference with an optional neural oracle trained on your data

It is a **minimal, legible implementation of Bayesian Program Induction**. It is not a language model, and it does not pretend to be one. It is a transparent, inspectable reasoning engine where every rule is a program you can read, edit, and compose.

### At a glance

| Property | Value |
|---|---|
| **Core algorithm** | Size-ordered, type-directed program synthesis (Occam's razor) |
| **Inference** | Symbolic search + optional neural amortization (DreamCoder-style) |
| **Storage** | Concept graph (not a lookup table) — nodes hold programs + dependencies |
| **Growth** | New concepts and invented abstractions are permanently registered |
| **Inspectability** | Every rule is a readable S-expression — no black boxes |
| **Dependencies** | Python 3.10+ stdlib; `torch` is optional |
| **Footprint** | ~2 000 lines of Python |

---

## Quick start

```bash
git clone https://github.com/<you>/OSTL.git
cd OSTL

# 1) Pure-symbolic mode — no dependencies beyond Python
python web_gui.py
# → opens http://127.0.0.1:8765/

# 2) Optional: neural accelerator (recommended)
pip install torch --index-url https://download.pytorch.org/whl/cpu
python train_neural.py        # ~30 seconds on CPU
python web_gui.py             # now uses neural proposals too
```

Then in the browser, paste these one at a time:

```
teach 3 -> 9
teach 5 -> 25
teach "hello" -> "OLLEH"
teach "abc" -> "CBA"
invent
concepts
```

You will see:

- Two concepts learned via **search** (first of each kind) and **reuse** (subsequent ones).
- `invent` promoting `(upper (reverse x0))` to `abstract_1` because both string concepts contain it.
- A live graph visualisation showing the dependency structure.

### Headless / SSH

The GUI is a **localhost web server**. It works over SSH, in WSL, and inside containers with no X server:

```bash
# From your local machine:
ssh -L 8765:localhost:8765 user@yourhost
# Then open http://localhost:8765/ locally
```

Bind to a public interface if you need remote access:

```bash
python web_gui.py --host 0.0.0.0 --no-browser
```

---

## How it works

OSTL implements the **three pillars** of one-shot concept learning. Each pillar is a small, independent module.

```
┌──────────────────────────────────────────────────────────────────┐
│  1. STRONG INDUCTIVE BIAS (dsl.py)                               │
│     Primitives encode "what kinds of rules are possible"         │
│     Type signatures prune impossible combinations                │
│                                                                  │
│  2. SIMPLICITY PRIOR (learner.py)                                │
│     Iterative deepening by AST size = minimum description length │
│     First fit = simplest explanation consistent with example     │
│                                                                  │
│  3. COMPOSITIONAL GROWTH (graph.py + abstract.py)                │
│     Learned rules become new primitives (vocabulary grows)       │
│     Recurring subtrees are promoted to first-class abstractions  │
└──────────────────────────────────────────────────────────────────┘
```

### Walk-through of `teach "hello" -> "OLLEH"`

```
1. Parse the input as a single variable of type STR
2. Enumerate programs by size:
   size 1: x0, "", "a"
   size 2: (upper x0), (reverse x0), (lower x0)
   size 3: (upper (reverse x0))  ← FIRST FIT
3. Verify: (upper (reverse x0)) applied to "hello" yields "OLLEH" ✓
4. Register as primitive + store in concept graph
```

The DSL's **type system** is what makes this tractable. Without it, size 3 contains ~10 000 combinations; with it, ~40.

### The concept graph

Every learned rule is a node. Edges express dependency:

```
concept_1  = (upper (reverse x0))       ← learned from "hello"
concept_2  = (concept_1 x0)             ← learned from "abc", reused concept_1
abstract_1 = (upper (reverse x0))       ← invented, promoted from the pattern
```

- `depth(concept_2) = 1` — it depends on one prior concept
- `dependents(concept_1) = {concept_2}` — who built on it
- `evaluate_trace()` returns the ordered list of sub-concepts that fired

Nothing here is a lookup table. Applying `concept_2` to `"xyz"` *runs the rule*, it does not retrieve a memorised answer.

### Optional: neural amortization

When `torch` is available, a small classifier (~40 k parameters) is trained on synthetic `(input, output) → program` pairs. At teach time it proposes the top-5 candidate programs, which are then verified symbolically. Falls back to pure search on any miss.

```
example ──▶ [neural oracle] ──▶ top-5 proposals
                                      │
                                      ▼
                                [verify symbolically]
                                      │
                          ┌───────────┴───────────┐
                          ▼                       ▼
                    match found              no match
                          │                       │
                          ▼                       ▼
                     store rule          [symbolic search]
```

Every teach where the program is in-vocabulary nudges the weights via `online_update` — the network specialises to **your** concept distribution over a session.

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                          web_gui.py                             │
│  HTTP server · static asset bootstrap · JSON API · GUI wiring   │
└────────────────────────────┬────────────────────────────────────┘
                             │
┌────────────────────────────▼────────────────────────────────────┐
│                            bot.py                               │
│  Command dispatch · teach/apply/why/explain/invent · persistence│
└──┬──────────────────────┬───────────────────────┬───────────────┘
   │                      │                       │
   ▼                      ▼                       ▼
┌──────────┐      ┌──────────────┐      ┌────────────────────┐
│learner.py│      │  neural.py   │      │     graph.py       │
│          │      │  (optional)  │      │                    │
│Typed BFS │      │ Amortized    │      │ Concept graph      │
│search    │      │ proposal net │      │ + dependency trace │
└────┬─────┘      └──────┬───────┘      └─────────┬──────────┘
     │                   │                        │
     ▼                   ▼                        ▼
┌──────────┐      ┌──────────────┐      ┌────────────────────┐
│program.py│      │   torch      │      │    abstract.py     │
│ AST      │      │  classifier  │      │  Abstraction       │
│ + to_dict│      └──────────────┘      │  discovery         │
└────┬─────┘                            └─────────┬──────────┘
     │                                            │
     ▼                                            ▼
┌─────────────────────────────────────────────────────────────────┐
│                            dsl.py                               │
│  Primitives · Type system · LEARNED_PRIMITIVES registry         │
└─────────────────────────────────────────────────────────────────┘
```

| File | Lines | Purpose |
|---|---|---|
| `dsl.py` | ~80 | Primitives, types, the growing primitive registry |
| `program.py` | ~80 | AST nodes, evaluation, serialization |
| `learner.py` | ~90 | Size-ordered, type-directed program search |
| `graph.py` | ~90 | Concept network with dependency tracing |
| `abstract.py` | ~70 | Recurring-subtree detection → invented primitives |
| `neural.py` | ~230 | Optional PyTorch program classifier |
| `bot.py` | ~200 | Orchestration (no GUI code) |
| `web_gui.py` | ~120 | HTTP server + asset bootstrap |
| `static/` | — | HTML / CSS / JS (auto-generated on first run) |

---

## Commands

| Command | Description |
|---|---|
| `teach <in> -> <out> [as <name>]` | Learn a rule from one example. `<in>` may be a scalar, list, or tuple. |
| `apply <name> <in>` | Apply a learned concept to a new input |
| `why <name> <in>` | Show the reasoning trace — which sub-concepts fired |
| `explain <name>` | Show the rule + its dependencies and dependents |
| `concepts` | List every concept, indented by dependency depth |
| `invent` | Discover new abstractions from recurring subtrees |
| `/export` · `/import` | Save / load the concept library as JSON |
| `<arithmetic expr>` | Evaluate a Python expression, e.g. `2*(3+4)` |
| `help` · `quit` | Standard |

### Example session

```
>>> teach 3 -> 9
Learned (** x0 2)  →  'concept_1'  [search]

>>> teach 5 -> 25
Learned (concept_1 x0)  →  'concept_2'  [neural]

>>> teach "hello" -> "OLLEH"
Learned (upper (reverse x0))  →  'concept_3'  [search]

>>> teach "abc" -> "CBA"
Learned (concept_3 x0)  →  'concept_4'  [neural]

>>> invent
Invented new abstractions:
  abstract_1 = (upper (reverse x0))   (found in: concept_3, concept_4)

>>> why concept_4 "xyz"
concept_4 = (concept_3 x0)
Sub-concepts fired (in order):
  concept_3 → 'ZYX'
Result: 'ZYX'
```

---

## Enhancing OSTL

The code is deliberately modular. Below are concrete, self-contained enhancements ranked by impact. Each has an existing research paper you can follow.

### 🥇 High-impact additions

#### 1. Richer DSL — higher-order primitives

**What:** Add `map`, `filter`, `lambda`, `if`, and recursion to `dsl.py`. This lets rules like `"a b c"` from `"abc"` become `(intercalate " " x0)` rather than a literal string.

**Where:** `dsl.py`. Add:

```python
def _higher_order():
    def if_fn(c, a, b):
        return a if c else b
    return Primitive("if", if_fn, [Type.BOOL, Type.ANY, Type.ANY], Type.ANY)
```

The learner's type system automatically prunes invalid compositions — no changes needed elsewhere.

**Effort:** Small · **Impact:** ⭐⭐⭐⭐⭐

#### 2. Neural-guided search (full DreamCoder recognizer)

**What:** Current `neural.py` is a classifier over a fixed vocabulary. Replace it with a **recursive recognition model** that scores partial programs, pruning the search as it goes.

**Where:** `neural.py` + a small change in `learner.py`: call `oracle.rank(candidates)` before evaluating each size bucket.

**Reference:** [DreamCoder (Ellis et al., 2021)](https://arxiv.org/abs/2006.08381)

**Effort:** Large · **Impact:** ⭐⭐⭐⭐⭐

#### 3. Library learning — iterative abstraction

**What:** After every teach, run `discover()` and register any new abstraction **without requiring the user to type `invent`**. Compress abstractions further into higher abstractions. This is the "chunking" that experts do.

**Where:** Wrap the `_teach` method's final block:

```python
def _teach(self, text):
    msg = self._do_teach(text)
    if not msg.startswith("Learned"):
        return msg
    self._invent()          # auto-invent
    self._prune_library()   # remove redundant concepts (new method)
    return msg
```

**Reference:** [DreamCoder §4 (Library Learning)](https://arxiv.org/abs/2006.08381)

**Effort:** Medium · **Impact:** ⭐⭐⭐⭐⭐

#### 4. Natural-language grounding

**What:** Parse "teach `"hello"` to uppercase reversed" for hint words (`uppercase`, `reverse`, `double`, `increment`) and pass them as a **prior over primitives** to the learner — primitives mentioned get their cost lowered.

**Where:** Add `learner.learn(examples, hints=...)`; in `_search`, when enumerating a `PrimitiveNode`, multiply the enumeration budget by `hint_weight(prim)`. Also add a hint-extraction regex in `bot._teach`.

**Impact:** This is the **single largest lever** for matching human one-shot performance, because humans use language to disambiguate. It's why `"alice" → "ECILA"` is obvious to a person but ambiguous to a bare searcher.

**Effort:** Medium · **Impact:** ⭐⭐⭐⭐⭐

### 🥈 Structural improvements

#### 5. Active disambiguation

When two or more programs fit the example, ask the user for a discriminating second input. Add a `probe <name> <input>` command; `why` already exposes the alternatives.

**Reference:** [Version-space algebra (Mitchell, 1982)](https://en.wikipedia.org/wiki/Version_space_learning)

**Effort:** Small · **Impact:** ⭐⭐⭐⭐

#### 6. Probabilistic scoring

Replace exact `pred == out` with a likelihood function — Gaussian for numbers, Levenshtein for strings. Enables learning from noisy examples and principled ranking of hypotheses.

**Where:** `learner._search` — change the fit check to return a score; keep top-k by `-(size + lambda * loss)`.

**Effort:** Small · **Impact:** ⭐⭐⭐⭐

#### 7. Persistence across sessions

```python
# In web_gui.AppServer.__init__:
try:
    self.bot.import_state(json.load(open("concepts.json")))
except FileNotFoundError:
    pass
# On shutdown (or via a POST /api/save endpoint):
json.dump(self.bot.export_state(), open("concepts.json", "w"), indent=2)
```

The `export_state` / `import_state` methods already round-trip every concept, including invented abstractions.

**Effort:** Trivial · **Impact:** ⭐⭐⭐⭐

#### 8. Meta-learning the prior

Train a **single neural prior** across a distribution of task types (string transforms, arithmetic, list operations), then fine-tune per user. This is what makes Matching Networks and MAML literally adapt in one gradient step.

**Reference:** [Matching Networks (Vinyals et al., 2016)](https://arxiv.org/abs/1606.04080), [MAML (Finn et al., 2017)](https://arxiv.org/abs/1703.03400)

**Effort:** Large · **Impact:** ⭐⭐⭐⭐⭐

### 🥉 GUI / UX enhancements

| Enhancement | Where | Effort |
|---|---|---|
| **Concept replay** — re-evaluate any concept against a saved test set | `web_gui.py` + `app.js` | Small |
| **Live program editor** — click a node, edit its AST, see the graph update | `app.js` + `/api/edit` | Medium |
| **Multi-example teach** — `teach 3->9, 4->16, 5->25` discriminates ambiguous hypotheses | `bot.py` | Small |
| **Concept diff** — show how a concept changed after a `teach` | `graph.py` | Small |
| **Session save/restore** — `/api/session` endpoints | `web_gui.py` | Trivial |

---

## Extending the DSL

Adding a primitive is a one-line change in `dsl.py`:

```python
BASE_PRIMITIVES = [
    _num("+", lambda a, b: a + b),
    _str1("upper", str.upper),
    _str1("reverse", lambda s: s[::-1]),
    # 🆕 your primitive:
    Primitive("title", str.title, [Type.STR], Type.STR),
]
```

That's it. The learner will automatically include it in the search, the neural oracle will be retrained on it (if you run `train_neural.py` again), and the frontend will render any concept that uses it.

**Rule of thumb for adding primitives:**
- Each primitive increases search space exponentially. Prefer **composable primitives** (`upper`, `reverse`) over **composite ones** (`upper_reversed`).
- Every primitive must be **total** on its declared input types, returning `None` on invalid inputs (the search treats `None` as a failure).
- Type annotations are **load-bearing** — a wrong type will silently prune valid programs.

---

## Contributing

Issues and pull requests welcome. Before contributing:

1. **Run the tests:** `python -m pytest tests/` (or `python test_smoke.py` if you haven't added pytest yet).
2. **Check the demo:** `python demo_training.py` must complete without errors.
3. **Follow the style:** stdlib-only in `dsl/program/learner/graph/abstract`; `torch` only in `neural.py`; no GUI imports outside `web_gui.py`.
4. **Document the change:** if you add a primitive, update the [Extending the DSL](#extending-the-dsl) section.

### Adding a new cognitive primitive

If you're implementing one of the enhancements above, the pattern is:

1. New file or new section in an existing module.
2. Expose a single public function / class with a clear docstring.
3. Wire it into `bot.py` behind a flag (`Bot(enable_x=True)`).
4. Add one line to the demo, one line to the README.

---

## FAQ

**Q: Is this a neural network or a symbolic system?**
**A:** Both. The symbolic engine guarantees correctness and inspectability. The neural oracle (optional) accelerates inference. Neither is a lookup table — the symbolic side stores *rules*, and the neural side stores *weights learned from your examples*.

**Q: Why not just use GPT-4?**
**A:** Because a language model's one-shot learning is *statistical*, not *guaranteed*. OSTL returns a program that provably fits the example. For most domains this is *too slow*; for some (spreadsheet formulas, data transformations, decision rules) it's *exactly the guarantee you need*. The right answer is to use both — GPT for the DSL, OSTL for the verification.

**Q: How does it generalise?**
**A:** Every learned rule is a *function*. `(** x0 2)` applied to `7` returns `49` — even though `7` was never seen. This is real generalisation, not interpolation.

**Q: What happens if the search fails?**
**A:** `teach` returns `"No consistent rule found"`. Increase `Bot(max_size=5)` (slower), add the missing primitive to the DSL, or reduce ambiguity by using a multi-example teach.

**Q: Is there a limit to how many concepts it can hold?**
**A:** In memory, no. In practice, above ~500 concepts the neural oracle retraining time grows and the concept graph becomes visually dense. Bump `hidden=256` in `train_oracle()` and add a `depth` filter to the graph for large libraries.

---

## Citations

OSTL is an implementation of ideas from:

- **DreamCoder** — Ellis, Wong, Nye, Sablé-Meyer, Morales, Hewitt, Cary, Solar-Lezama, Tenenbaum. *DreamCoder: Bootstrapping inductive program synthesis with wake-sleep library learning.* PLDI 2021. [arXiv:2006.08381](https://arxiv.org/abs/2006.08381)
- **Bayesian Program Learning** — Lake, Salakhutdinov, Tenenbaum. *Human-level concept learning through probabilistic program induction.* Science 2015. [doi:10.1126/science.aab3050](https://doi.org/10.1126/science.aab3050)
- **Matching Networks** — Vinyals, Blundell, Lillicrap, Kavukcuoglu, Wierstra. *Matching Networks for One Shot Learning.* NeurIPS 2016. [arXiv:1606.04080](https://arxiv.org/abs/1606.04080)
- **Neural Program Synthesis** — Balog, Gaunt, Brockschmidt, Nowozin, Yang. *DeepCoder: Learning to Write Programs.* ICLR 2017. [arXiv:1611.01989](https://arxiv.org/abs/1611.01989)

---

## License

MIT — see [LICENSE](LICENSE).

<div align="center">

**If OSTL taught you something, ⭐ the repo.**

</div>