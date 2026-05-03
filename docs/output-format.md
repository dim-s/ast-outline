# Output format

`ast-outline` has two output modes: **outline** (per-file, detailed)
and **digest** (multi-file, compact). Both are designed to be
**parseable cold by an LLM agent** — no out-of-band reference doc
needed.

## Outline format

```text
# path/to/Player.cs (1247 lines)
class Player : Entity, IDamageable                        L12-340
  public int Health                                       L18-18
  public int Speed                                        L19-19
  public Player(int initialHealth)                        L25-32
  public void TakeDamage(int amount)                      L42-58
  public void Heal(int amount)                            L60-72
  private void Die()                                      L74-89
  ...
```

Each row is:

```
<indent> [Attr] <modifiers> <kind> <Name> [: bases] L<start>-<end>
```

Method bodies are **omitted**. The line range points at the body —
agents can `show` it or `Read` that exact slice.

---

## Digest format

`digest` is denser: file headers + a one-line legend + collapsed
callables.

```text
# legend: name()=callable, name [kind]=non-callable, [N overloads]=N callables share name, [deprecated]=obsolete, ...

# src/Combat/Player.cs [medium] (1247 lines)
class Player : Entity, IDamageable
  Health, Speed, Mana
  TakeDamage(), Heal(), Die() [3×]
  Update() [override], FixedUpdate() [override]
  cooldowns [property]

# src/Combat/Enemy.cs [tiny]
class Enemy : Entity
  PatrolTo(), Attack() [async], Despawn()
```

The legend is one line, intentionally — the format is
self-explanatory once you see the legend once, and agents don't need
to look it up again per query.

---

## Size labels

Each file in a digest gets a label based on **outline output size**:

| Label | Approximate range | Meaning |
| --- | --- | --- |
| `[tiny]` | < ~500 tokens | Outline is roughly the same size as the source — `Read` directly is fine. |
| `[medium]` | ~500–5000 tokens | Outline meaningfully compresses — prefer it. |
| `[large]` | 5000+ tokens | Outline output itself can run long; prefer `digest`, then `show` on specific symbols. |

These labels are about **how much you save with the outline**, not the
file's intrinsic complexity. A large generated file might still be
`[large]` even though no human writes it.

---

## Method-level marker tags

Modifiers that are interesting to an agent surface as bracketed tags
after the method name:

| Tag | Meaning |
| --- | --- |
| `[async]` | `async` / `suspend` callable |
| `[unsafe]` | Rust `unsafe fn` |
| `[const]` | Rust / C# `const fn` / `constexpr` |
| `[static]` | Static method or function (varies per language) |
| `[abstract]` | Abstract / un-implemented |
| `[override]` | Overrides a base / parent |
| `[classmethod]` | Python `@classmethod` |
| `[property]` | Python `@property`, C# property accessor, JVM property |
| `[deprecated]` | Marked deprecated / obsolete |
| `[N×]` | N adjacent callables share the name (overloads) |

Type-level tags (`[deprecated]`, modifier prefixes like `sealed`,
`abstract`, `partial`) appear **before** the kind keyword.

---

## Inheritance

Both renderers append `: Base, Trait` to type headers when the AST
gives bases / interfaces / traits — so the agent sees the hierarchy
without a separate query.

Examples:

```text
class Player : Entity, IDamageable
trait Drawable : Component
struct Vec3 : Copy, Clone
class TimerService : ITimerService, IDisposable
```

For Rust, `impl Trait for Foo` blocks **regroup under the target type**
and add `Trait` to the bases list — there are no synthetic
`impl_Foo` shadows polluting the outline.

---

## Imports (`--imports`)

When `--imports` is passed, each file header gets an extra line:

```text
# src/Combat/Player.cs [medium] (1247 lines)
imports: using UnityEngine; using System.Linq; using Combat.Damage;
class Player : Entity, IDamageable
  ...
```

The import line is **verbatim** from the source — no normalization,
no de-aliasing. An agent looking at `IDamageable` can grep the
imports for where it lives.

---

## Errors and broken outlines

When tree-sitter recovers from syntax errors, the outline is kept
but a warning surfaces. In `outline`:

```text
# path/to/Player.cs (1247 lines) WARNING: 3 parse errors
class Player : Entity                                     L12-340
  ...
```

In `digest`, the file gets a `[broken]` tag:

```text
# src/Combat/Player.cs [medium] [broken]
  ...
```

When you see `[broken]`, treat the outline as best-effort and read
the affected region directly with `Read` / `show`.
