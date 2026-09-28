# Type Patterns and Escape Hatches: Definitions, Grounding, and Parser Revision Plan

Status: planning document, no code changed yet. Owner: Tayyib. Task on the shared plan: "Revise the regex parser and define the escape hatches."

Date: 2026-09-14

---

## 1. Why this document exists

The reviewer reports on the FSE draft made three points that this document answers:

1. "Construct" and "advanced construct" are undefined, and the catalogue mixes heterogeneous things.
2. The escape-hatch classification is asserted, not grounded. `.unwrap()` and `as` are not equivalent to `any` or `dynamic`, and the paper never says why they are grouped together.
3. The construct counter (the regexes) was never validated at the occurrence level. Only PR-level relevance was validated.

Everything downstream (RQ1, RQ2, the cross-language comparison, the figures) depends on the catalogue being defensible. So the catalogue is fixed first, from official language documentation and peer-reviewed evidence, and only then is the parser rewritten to match it.

Revised research questions this catalogue serves:

- **RQ1 (type patterns).** How do AI agents and human developers use the type-system patterns of TypeScript, C#, and Rust in pull requests? Unit: construct occurrences on added lines, per PR and per 100 changed lines.
- **RQ2 (escape hatches).** How do AI agents and human developers use escape hatches, the subset of patterns that opt out of a compile-time guarantee? Same units, plus additions versus removals.
- **RQ3 (acceptance).** Unchanged, TypeScript only unless comparable human baselines are rebuilt.

---

## 2. Definitions

### 2.1 Type pattern

A **type pattern** is a syntactic construct, documented in the language's official reference, whose primary purpose is to declare, constrain, narrow, convert, or opt out of static type information. Constructs whose primary purpose is control flow, memory management, or concurrency are excluded even when they interact with types (this removes `match`, `if let`, `Arc`/`Mutex`, `#[derive]`, `delegate`, and attributes from the current catalogue).

Inclusion test, all three must hold:

- **P1 Documented.** It has its own section or subsection in the official language reference or handbook (TypeScript Handbook, C# language reference on Microsoft Learn, The Rust Reference or The Rust Programming Language book).
- **P2 Type-directed.** The documentation describes its effect in terms of types, type checking, nullability, or safety guarantees.
- **P3 Detectable.** It has a lexical signature that a line-level regex on a diff can recognise with precision above 0.9 on a manual sample (Section 6). Constructs that fail P3 are dropped, not approximated.

### 2.2 Escape hatch

An **escape hatch** is a type pattern that lets the author avoid establishing, at compile time, a property the language would otherwise require, so that a class of errors normally reported by the compiler is instead deferred to runtime, made undefined, or silently accepted.

A construct is classified as an escape hatch if **at least one** of E1, E2, or E3 holds. Any one form of grounding is sufficient; the tables record whichever apply.

- **E1 Official documentation.** The language reference says the construct disables, bypasses, or suppresses a static check, tells the reader they are taking on responsibility the compiler normally carries, or advises using it sparingly. Quotes are recorded in the tables below.
- **E2 Officially maintained linter rule.** typescript-eslint, the C# compiler's own nullable warnings and Roslyn analyzers, or rust-clippy ships a rule against it. This is evidence that the ecosystem treats the construct as a liability, independent of our judgement.
- **E3 Prior study.** Published work associates it with defects, unsoundness, panics, or vulnerabilities. Peer-reviewed is preferred but a language-design paper or a documented case study also counts.

Rationale for the disjunction: requiring all three would exclude constructs that are uncontroversially escape hatches but understudied. C# `dynamic` and the null-forgiving operator have no usage study at all, and `.unwrap()` is not described by the Rust Book as bypassing a check even though clippy lints it and prior work ties it to panic bugs. Under a conjunctive rule we would lose the C# arm and the Rust secondary metric for lack of literature, not for lack of validity.

**Two axes, not one ordinal tier.** The earlier draft used a single A/B tier and it contradicted itself on three entries. Classification now records two independent properties.

Axis 1, **what is waived**:

- **Tier A, removed.** The compile-time guarantee is waived and no check replaces it. Examples: `any`, both `!` operators, `unsafe`, `transmute`, Rust `as`.
- **Tier B, relocated.** The guarantee is re-established at runtime by a check the language inserts. Examples: C# `dynamic` (runtime binder), C# `(T)x` and `as`, `.unwrap()`, `RefCell::borrow_mut`.

Axis 2, **how failure manifests**: `none` (types erased, nothing happens at runtime), `silent-lossy` (a defined but wrong or truncated value), `undefined` (undefined behavior), `loud` (exception or panic at the point of failure).

The axes are orthogonal and neither alone is the story. TypeScript `any` is A/none, C# `dynamic` is B/loud, Rust `as` is A/silent-lossy, `.unwrap()` is B/loud, `unsafe` is A/undefined. Note the consequence, which is a finding rather than a problem: C# `dynamic` is strictly safer than TypeScript `any`, so the two are analogues by *purpose* (Section 6) and not by *risk*. Tier A and Tier B counts are never summed.

Everything else is **not an escape hatch** and is subdivided into:

- **Tier C, expressiveness.** Constructs that add type information or make types more precise (generics, conditional types, pattern matching, trait bounds).
- **Tier D, safety-enhancing.** Constructs whose documented purpose is to *restore* or strengthen a guarantee (`unknown`, `satisfies`, `#nullable enable`, `TryFrom`, `?` operator). These are the "positive" counterpart to RQ2 and are worth reporting alongside escape hatches.

### 2.3 Evidence codes used in the tables

- **D** official documentation (quote or section given)
- **L** linter rule, with the rule name and the ruleset it belongs to
- **P** peer-reviewed publication, numbered in Section 8

---

## 3. TypeScript catalogue

Sources: TypeScript Handbook (Everyday Types, Narrowing, Type Manipulation chapters, tsconfig reference), release notes for 2.0, 2.6, 3.0, 3.9, 4.9, typescript-eslint rule docs.

### 3.1 Escape hatches

| ID | Construct | Syntax | Tier | Evidence | Detection notes |
|---|---|---|---|---|---|
| TS-E1 | Explicit `any` annotation | `: any`, `<any>`, `any[]`, `Record<string, any>`, `as any` | A / none | D: Handbook, Everyday Types: "When a value is of type `any`, you can access any properties of it, call it like a function, assign it to (or from) a value of any type, or pretty much anything else that's syntactically legal." L: `@typescript-eslint/no-explicit-any` (recommended). P: [1] formalises `any` as the source of unsoundness; [3] finds refraining from `any` correlates with better quality; [2] quantifies bugs static typing could catch. | Current regex only catches `:\s*any\b`. Must also count `as any`, `<any>`, `any[]`, `any>` inside generic args, and function `(...args: any[])`. Exclude `anything`, identifiers, strings, comments. |
| TS-E2 | Type assertion to an unrelated type ("double assertion") | `x as unknown as T`, `x as any as T`, `<T><unknown>x` | A / none | D: Handbook, Everyday Types: "TypeScript only allows type assertions which convert to a more specific or less specific version of a type. This rule prevents 'impossible' coercions"; the documented workaround is asserting through `any`/`unknown`. P: [1], [4] (unsoundness of assertions). | Signature `as (unknown\|any) as` is unambiguous. Count separately from plain `as T`. |
| TS-E3 | Plain type assertion | `x as T`, `<T>x` (non-JSX files only) | A / none | D: Handbook: "TypeScript only allows type assertions which convert to a more specific or less specific version" and assertions are not checked at runtime. L: `consistent-type-assertions` (stylistic), `no-unsafe-type-assertion` (strict). P: [4] lists assertions as one of the seven sources of unsoundness. | Exclude `as const` (Tier D) and `import ... as`, `export ... as`, mapped-type key remapping `[K in keyof T as ...]`. Angle-bracket form only in `.ts`, never `.tsx`. **Construct-validity threat to state in the paper:** widening to a supertype is sound while narrowing to a subtype is not, and no regex can tell them apart without type information, so this counter pools a safe and an unsafe use. |
| TS-E4 | Non-null assertion | `x!.y`, `x![0]`, `x!()`, `x!;` | A / none | D: Handbook, Everyday Types: "Writing `!` after any expression is effectively a type assertion that the value isn't `null` or `undefined` ... it's important to only use `!` when you know that the value can't be `null` or `undefined`." Release notes 2.0. L: `no-non-null-assertion` (strict). | Current regex `!\s*[.\[(]` also matches `!(cond)` logical negation and `!==`. Require an identifier, `)` or `]` immediately before `!`, and forbid `=` after. |
| TS-E5 | Compiler-directive suppression | `// @ts-ignore`, `// @ts-expect-error`, `// @ts-nocheck` | A / none | D: release notes 2.6 (`@ts-ignore` "suppresses all errors on the following line"), 3.9 (`@ts-expect-error`), 3.7 (`@ts-nocheck` in .ts). L: `ban-ts-comment` (recommended). | Trivial to detect. Count the three separately; `@ts-expect-error` is the documented safer form. Not in the current catalogue, must be added. |
| TS-E6 | Untyped function type | `: Function` | A / none | D: Handbook, More on Functions: `Function` "has the special property that values of type `Function` can always be called; these calls return `any`". L: `no-unsafe-function-type` (recommended). | `Function` is the only genuine escape hatch of the three the earlier draft grouped here. `{}` means "anything non-nullish" and member access on it is still checked, and `Object` is similar, so both are weak types rather than escape hatches. Recommendation in Section 9: drop them, or report them separately as weak types. |
| TS-E7 | Index signature typed `any` | `[key: string]: any` | A / none | Special case of TS-E1; counted under TS-E1 but flagged, because it spreads `any` across every property access. | Regex `\[\s*\w+\s*:\s*(string\|number\|symbol)\s*\]\s*:\s*any`. |
| TS-E8 | User-defined type guard | `function isFoo(x): x is Foo` | B / silent | D: Handbook, Narrowing: the compiler trusts the predicate; a wrong predicate is not detected. P: [4]. Runtime behaviour is whatever the body does, so failure is not silent by construction. | Current regex is fine after requiring `:\s*\w+\s+is\s+[A-Z]`. Counted as Tier B because it moves the check to user code, not because it removes it. |
| TS-E9 | Strictness opt-out in config | `"strict": false`, `"noImplicitAny": false`, `"strictNullChecks": false` in `tsconfig.json` | A / none | D: tsconfig reference. | Counted per PR as a binary flag, not per line. Config files must be included in the file filter for this only. |

### 3.2 Safety-enhancing (Tier D)

| ID | Construct | Syntax | Evidence |
|---|---|---|---|
| TS-D1 | `unknown` | `: unknown`, `as unknown` (when not followed by another `as`) | D: release notes 3.0: "the type-safe counterpart of `any`". Prefer-unknown guidance in [5]. |
| TS-D2 | `satisfies` | `expr satisfies T` | D: release notes 4.9: validates against a type without widening. |
| TS-D3 | `as const` | `... as const` | D: release notes 3.4, const assertions. Narrows, does not widen. |
| TS-D4 | `readonly` modifier / `Readonly<>` | `readonly x:`, `readonly [`, `Readonly<T>` | D: Handbook, Object Types. |
| TS-D5 | Replacement of `any` by a concrete type on the same line (removal of TS-E1) | `-  x: any` / `+  x: Foo` | Derived metric, already implemented as `any_replacement`. Keep. |
| TS-D6 | Optional chaining | `obj?.prop`, `fn?.()` | D: release notes 3.7. Added during implementation: it is the safe counterpart of TS-E4, handling absence instead of asserting it away, and reporting the two together makes the contrast visible. |
| TS-D7 | Nullish coalescing | `a ?? b` | D: release notes 3.7. Same rationale as TS-D6. Excludes `??=`. |

### 3.3 Expressiveness (Tier C)

Keep, with tightened regexes: generics in declarations (TS-C1), conditional types (TS-C2), `infer` (TS-C3), mapped types (TS-C4), key remapping (TS-C5), template literal types (TS-C6), `keyof` (TS-C7), `typeof` in type position (TS-C8), indexed access (TS-C9), utility types (TS-C10), union types (TS-C11), intersection types (TS-C12), discriminated-union tags (TS-C13), optional properties (TS-C14).

Drop: `recursive_type_count` (the file itself calls the heuristic "highly unreliable", fails P3), `in_operator_count` (duplicates TS-C4), `unique_symbol` (too rare to analyse), `const_assertion_count` (duplicate of TS-D3).

Added during implementation: TS-C15 `enum` declarations, which are type declarations and satisfy P1-P3.

Dropped from the previously reported set, with the reason: **decorators** (metadata, fails P2, not type-directed) and **abstract classes** (nominal declaration, fails P2). Both appeared in the old Figure 3, where decorators were the highest-frequency TypeScript "construct" for agents. Removing them changes that figure materially, so `docs/paper_updates.md` records it. **Optional chaining** and **nullish coalescing** were also in the old set as expressiveness constructs; they are retained but reclassified to Tier D, where they belong.

---

## 4. C# catalogue

Sources: C# language reference on Microsoft Learn (Types, `dynamic`, Nullable reference types, null-forgiving operator, Type-testing operators and cast expression, Unsafe code, Pattern matching, Generics), .NET code-analysis rule reference, nullable-reference-types specification in dotnet/csharplang.

### 4.1 Escape hatches

| ID | Construct | Syntax | Tier | Evidence | Detection notes |
|---|---|---|---|---|---|
| CS-E1 | `dynamic` type | `dynamic x`, `(dynamic)`, `<dynamic>`, `dynamic[]`, `dynamic` return/parameter type | B / loud | D: Microsoft Learn, "Built-in reference types": "The `dynamic` type indicates that use of the variable and references to its members bypass compile-time type checking. Instead, these operations are resolved at run time." P: [6] design paper states the purpose is to defer checking; [7] usability experiment. No usage study of `dynamic` in the wild exists; grounding is D plus the language-design paper, which E1 alone satisfies. | Current regex `\bdynamic\s+\w+` misses casts, generic args, and arrays. Exclude identifiers like `dynamicValue`, string literals, and `[Dynamic]`/`DynamicAttribute`. Tier B because the DLR re-establishes member resolution at runtime and failure raises `RuntimeBinderException`. It is the *purpose*-analogue of TS `any`, not the risk-analogue. |
| CS-E2 | Null-forgiving operator | `x!.y`, `x!;`, `default!`, `null!` | A / none | D: Microsoft Learn, "! (null-forgiving) operator": "has no effect at run time. It only affects the compiler's static flow analysis." The nullable-reference-types spec and the guide say to use it sparingly since "each occurrence is a place where the compiler can no longer protect you". L: compiler warnings CS8600 to CS8625 are what it suppresses. | Same disambiguation as TS-E4: identifier, `)` or `]` immediately before `!`; forbid `=` after. Only meaningful in files or projects with nullable enabled; record CS-D1/CS-E3 per PR to condition on it. |
| CS-E3 | Nullable context opt-out | `#nullable disable`, `#nullable disable warnings`, `<Nullable>disable</Nullable>` in `.csproj` | A / none | D: Microsoft Learn, "Nullable reference types", nullable context. | Split the current `nullable_directive_count` into enable (Tier D) and disable/restore (Tier A). |
| CS-E4 | Warning suppression | `#pragma warning disable CS8xxx`, `[SuppressMessage(...)]` | A / none | D: Microsoft Learn, `#pragma warning`; code-analysis suppression docs. | Count only when the suppressed ID is in the nullable range CS8600 to CS8655 or the suppression is unqualified. Not in the current catalogue, must be added. |
| CS-E5 | `unsafe` code | `unsafe { }`, `unsafe` modifier, pointer types `T*`, `fixed`, `stackalloc` outside `Span<T>`, `delegate*` | A / undefined | D: Microsoft Learn, "Unsafe code, pointer types, and function pointers": unsafe code "isn't verified" and the CLR cannot guarantee memory safety; requires `AllowUnsafeBlocks`. | Regex `\bunsafe\b` plus `\bfixed\s*\(`. Exclude comments and strings. Not in the current catalogue, must be added. |
| CS-E6 | Unchecked reinterpretation APIs | `Unsafe.As<`, `Unsafe.AsRef`, `MemoryMarshal.Cast<`, `MemoryMarshal.AsRef` | A / undefined | D: `System.Runtime.CompilerServices.Unsafe` API docs state the methods perform no type checks. | Low frequency; combined counter. |
| CS-E7 | Explicit cast expression | `(T)x` where `T` is a type | B / loud | D: Microsoft Learn, "Type-testing operators and cast expressions": a cast that fails "throws an `InvalidCastException`". The check is moved to runtime, not removed. | Current regex `\([A-Z]\w*[<>\[\]]*\)\s*\w+` also matches method calls with a single capitalised argument, e.g. `Foo(Bar) x`. Require the cast to be followed by an identifier, `(`, or another cast, and exclude `(Task)`-style patterns inside `await`. Precision must be checked (Section 6). |
| CS-E8 | `as` operator | `x as T` | B / silent | D: same page: `as` "returns `null` instead of throwing". Tier B because the result is a well-typed nullable value the compiler continues to track, so the guarantee is relocated to the null check rather than removed. Failure is silent, which is why the failure-mode column matters. | Exclude `using X as`, lambda bodies, and string content. |
| CS-E9 | Boxing to `object` as a declared type | `object x =`, `: object`, `List<object>` | B / loud | D: Microsoft Learn, "Boxing and unboxing": unboxing to the wrong type throws at runtime. | Low value; keep as a secondary counter only if precision is good. |
| CS-E10 | Reflection-based invocation | `.GetMethod(`, `.Invoke(`, `Activator.CreateInstance`, `Type.GetType(` | B / loud | D: reflection docs; all binding is by string at runtime. | Optional, secondary. |

### 4.2 Safety-enhancing (Tier D)

| ID | Construct | Syntax | Evidence |
|---|---|---|---|
| CS-D1 | Nullable context enable | `#nullable enable`, `<Nullable>enable</Nullable>` | D: Nullable reference types docs. |
| CS-D2 | Nullable annotations | `string?`, `T?` on reference types | D: same. Note this is only meaningful under CS-D1. |
| CS-D3 | Pattern-based type tests | `x is T y`, `is not null`, `switch` with type patterns | D: Pattern matching docs; replaces cast-then-check with a checked narrowing. |
| CS-D4 | `required` members, `init` setters, `record` | | D: C# 9 and 11 docs; they strengthen construction-time invariants. |
| CS-D5 | Generic constraints | `where T : ...` | D: Generics constraints docs. |

### 4.3 Expressiveness (Tier C)

Keep with tightened regexes: generic type parameters in declarations only (CS-C1, replacing the current `<[^<>]+>` which matches every generic *use* and every HTML tag in a string), variance (CS-C2), tuples (CS-C3), type aliases via `using X = ...` (CS-C4), `readonly struct` / `ref struct` / `ref readonly` (CS-C5, low frequency, combine).

Drop: `var_count` (implicitly typed locals are fully static, documented as such; not a type pattern of interest and heavily confounded by style), `attribute_count`, `delegate_count`, `inheritance_count`, `typeof_count` (not type-directed in the P2 sense).

---

## 5. Rust catalogue

Sources: The Rust Programming Language (ch. 9 Error Handling, ch. 10 Generics/Traits/Lifetimes, ch. 15.5 `RefCell<T>`, ch. 20.1 Unsafe Rust), The Rust Reference (Type cast expressions, Unsafety, Attributes), The Rustonomicon, rust-clippy lint list, std documentation for `Option`, `Result`, `mem::transmute`.

### 5.1 Escape hatches

| ID | Construct | Syntax | Tier | Evidence | Detection notes |
|---|---|---|---|---|---|
| RS-E1 | `unsafe` block or function | `unsafe { }`, `unsafe fn`, `unsafe impl`, `unsafe trait`, `unsafe extern` | A / undefined | D: Book ch. 20.1: unsafe Rust "gives us the ability to ... tell the compiler 'trust me'"; the five "superpowers" are explicitly the checks the compiler stops performing. L: `undocumented_unsafe_blocks` (restriction), `#![forbid(unsafe_code)]` lint. P: [8], [9], [10], [11], [12]. | Split into block, fn, impl, trait sub-counters, and give `unsafe impl Send` / `unsafe impl Sync` its own counter: both [8] and [10] single it out as the pattern where hand-written soundness arguments most often fail, and it is currently buried in the aggregate. The existing single token counter also matches `// SAFETY` prose because comments are not stripped. Strip comments before counting. |
| RS-E2 | `transmute` and unchecked reinterpretation | `mem::transmute`, `transmute_copy`, `*const T as *const U`, `from_raw_parts` | A / undefined | D: Rustonomicon, Transmutes: "This is really, truly, the most horribly unsafe thing you can do in Rust." L: `transmute_ptr_to_ptr`, `useless_transmute`, `wrong_transmute` (correctness). P: [10], [11]. | Already unsafe-only, so always a subset of RS-E1; count separately because it is the strongest form. |
| RS-E3 | Lint suppression | `#[allow(...)]`, `#![allow(...)]`, `#[allow(unsafe_code)]`, `#[allow(clippy::unwrap_used)]` | A / none | D: Rust Reference, Lint check attributes. | Count `allow` only; `expect(lint)` (stable since 1.81) is the checked form and goes in Tier D. Not in the current catalogue, must be added. |
| RS-E4 | `_unchecked` API calls | `.get_unchecked(`, `unwrap_unchecked(`, `from_utf8_unchecked(`, `unreachable_unchecked(` | A / undefined | D: std docs mark each as `unsafe fn` with "calling this on an invalid value is undefined behavior". | Always inside RS-E1; separate counter. |
| RS-E5 | `.unwrap()` / `.expect()` | `.unwrap()`, `.expect("...")` on `Option`/`Result` | B / loud | D: Book ch. 9.2: `unwrap` "will call the `panic!` macro for us" and ch. 9.3 "To `panic!` or Not to `panic!`" says to prefer returning `Result` in library code. L: `unwrap_used`, `expect_used` (restriction). P: [13] reports 26 panic issues caused by `unwrap`/`expect` fixed by introducing `match`; [14] studies panic bugs. | Qualifies on E2 and E3, not E1: the Book does not say a static check is bypassed, because the compiler does force the author to handle the `Option`/`Result` and `.unwrap()` is one legal way to do so. State this explicitly in the paper rather than implying it bypasses the type checker. What is waived is the obligation to *handle* absence or failure without aborting, and the lint plus the panic-bug literature is the grounding. Regex `\.\s*(unwrap\|expect\|unwrap_err\|expect_err)\s*\(`; `unwrap_or`, `unwrap_or_else`, and `unwrap_or_default` are Tier D handling and excluded. |
| RS-E6 | Panicking macros used as control flow | `panic!(`, `unreachable!(`, `todo!(`, `unimplemented!(` | B / loud | D: std macro docs; `todo!` is documented as a placeholder. L: `panic`, `unreachable`, `todo`, `unimplemented` (restriction). | Exclude inside `#[test]` functions and `#[should_panic]` where feasible; at minimum exclude files under `tests/` and `benches/`. |
| RS-E7 | Direct indexing of slices and maps | `v[i]`, `map[&k]` | B / loud | D: std docs: indexing "panics if out of bounds". L: `indexing_slicing` (restriction). | **Recommend dropping.** What is waived is a bounds check, not a type check, so it sits outside the type-pattern definition in Section 2.1. Regex precision is also poor against array types, attributes, and macros. Keep only if the paper widens its scope to compiler-enforced obligations generally. |
| RS-E8 | `as` numeric and pointer casts | `x as u32`, `x as usize`, `p as *const T` | A / silent-lossy | D: Rust Reference, Type cast expressions: numeric casts are never checked; docs recommend `From`/`TryFrom` for fallible conversions. L: `as_conversions` (restriction), `cast_possible_truncation`, `cast_sign_loss`, `cast_possible_wrap` (pedantic). | Tier A: no runtime check is inserted, so the conversion guarantee is removed rather than relocated. Semantics differ by direction and must be stated correctly in the paper. Integer to integer truncates and wraps. Float to integer truncates toward zero and *saturates* at the bounds, with NaN mapping to 0, since Rust 1.45; before 1.45 it was undefined behavior. Exclude `use x as y`, `as_ref`, `as_str`, and string content. Current regex is close; add `*mut`/`*const` and `_` targets. |
| RS-E9 | Runtime-checked interior mutability | `RefCell<`, `.borrow_mut()`, `.borrow()`, `Cell<` | B / loud | D: Book ch. 15.5: "the borrowing rules' invariants are enforced at runtime ... if you break these rules, your program will panic". | Count `RefCell`/`Cell` type uses and `.borrow_mut()` calls separately. Excludes `Mutex`/`RwLock` (concurrency, not type). |
| RS-E10 | Type erasure via `dyn Any` and downcasting | `dyn Any`, `.downcast_ref::<`, `.downcast::<` | B / loud | D: std `Any` docs: downcasting is a runtime type test. | Low frequency; secondary. |

### 5.2 Safety-enhancing (Tier D)

| ID | Construct | Syntax | Evidence |
|---|---|---|---|
| RS-D1 | `?` operator | `expr?` | D: Book ch. 9.2, propagating errors. Exclude `?Sized` and generics. |
| RS-D2 | Checked conversions | `TryFrom`, `try_from(`, `try_into(`, `checked_add(` etc. | D: std docs. |
| RS-D3 | Non-panicking `Option`/`Result` handling | `unwrap_or`, `unwrap_or_else`, `unwrap_or_default`, `ok_or`, `map_err`, `if let Some`, `let else` | D: Book ch. 9. |
| RS-D4 | `#[expect(lint)]` and `#![forbid(unsafe_code)]` / `#![deny(unsafe_code)]` | | D: Reference, lint attributes. |
| RS-D5 | `// SAFETY:` comment attached to an unsafe block | | L: `undocumented_unsafe_blocks`; the ratio of documented to undocumented unsafe blocks is a direct quality signal used in [8]. |

### 5.3 Expressiveness (Tier C)

Keep with tightened regexes: generic parameters in declarations (RS-C1, not every `<...>`), lifetimes (RS-C2; the current `'[a-zA-Z_]\w*` also matches char literals like `'a'`, require preceding `&`, `<`, `,` or `:` and no closing quote), trait bounds (RS-C3), `where` clauses (RS-C4), `impl Trait` (RS-C5), `dyn Trait` (RS-C6), type aliases (RS-C7), associated types inside `impl`/`trait` (RS-C8), `PhantomData` (RS-C9), `enum` definitions (RS-C10), `trait` definitions (RS-C11), `Send`/`Sync` bounds (RS-C12), `Option`/`Result` in type position (RS-C13).

Drop: `match_count`, `if_let_count` (control flow; moved to RS-D3 only when used on `Option`/`Result`), `derive_count`, `struct_count`, `impl_block_count`, `smart_pointer_count` (concurrency and ownership, not type patterns), `box_dyn_count` (subset of RS-C6).

Implementation note: RS-E1 is realised as six counters, not one. `RS-E1` block, `RS-E1b` fn, `RS-E1c` impl, `RS-E1d` `impl Send`/`impl Sync`, `RS-E1e` trait, and `RS-E1f` the aggregate `unsafe` token that remains the headline RQ2 metric for Rust. The sub-counters are declared as children of the aggregate in `NESTED_KEYS` so they are never added to it.

---

## 6. Cross-language mapping

This is the table the paper needs to make the "spectrum" argument honestly. Rows are *what check is opted out of*, not surface syntax.

| Guarantee opted out of | TypeScript | C# | Rust | Comparable across languages? |
|---|---|---|---|---|
| Static typing of a value entirely | TS-E1 `any` (A/none) | CS-E1 `dynamic` (B/loud) | none | Same purpose, different risk. Rust has no construct that erases static typing while remaining safe, which is itself a finding. `dyn Any` is a checked downcast and belongs in the conversion row, not here. |
| Static check of a specific conversion | TS-E3 `as T`, TS-E2 double assertion (A/none) | CS-E7 `(T)x` (B/loud), CS-E8 `as` (B/silent), RS-E10 analogue | RS-E8 `as` (A/silent-lossy), RS-E10 `dyn Any` downcast (B/loud) | Yes, but the failure modes differ across all three and must be reported, not averaged. |
| Null / absence check | TS-E4 `!` (A/none) | CS-E2 `!` (A/none) | RS-E5 `.unwrap()` (B/loud) | TS and C# are exact analogues: both are compile-time-only, with no runtime effect. Rust's is not an analogue by mechanism, only by intent. Report side by side, never pooled. |
| Compiler diagnostics as a whole | TS-E5 `@ts-ignore`, TS-E9 config | CS-E3, CS-E4 | RS-E3 `#[allow]` | Yes, all A. |
| Memory safety | none | CS-E5 `unsafe` | RS-E1 `unsafe`, RS-E2, RS-E4 | C# and Rust yes. |
| Aliasing / borrow rules | none | none | RS-E9 `RefCell` | Rust only. |

Headline RQ2 metric per language, justified by sharing a row rather than by loose analogy: `any` (TS), `dynamic` plus `!` (C#), `unsafe` (Rust). Secondary metrics are the remaining escape hatches for that language. Tier A and Tier B counts are reported separately and never summed, and every reported figure carries its failure mode so that a reader can see that "escape hatch" does not mean the same risk in each column.

**Diagnostic suppression is reported as its own family, not pooled with the rows above.** The suppression constructs (TS-E5, TS-E9, CS-E3, CS-E4, RS-E3) disable the checker's *reporting* rather than the type system's guarantee, and their scope is not commensurable with per-expression constructs: one null-forgiving operator waives one check, while one `#nullable disable` at the top of a file waives an unbounded number. Their unit is therefore files affected and PRs containing, not occurrences per 100 lines. The configuration-file entries cannot share a line-based denominator at all.

**Opportunity denominators.** Per-PR and per-100-changed-line rates both ignore whether the construct *could* have appeared. The C# null-forgiving operator only occurs where the nullable context is enabled, `unsafe` clusters in systems and foreign-function crates, and `any` needs an annotation site. Because the agent and human corpora come from different sources, an unadjusted "agents use more X" result is partly a statement about which files were touched. Each headline construct therefore needs an opportunity denominator (`!` per nullable-enabled changed line, `any` per annotation site added, `unsafe` per changed line in crates that already contain `unsafe`), and repository must enter the model as a grouping factor regardless.

**Gross, not net.** The reported RQ2 metric is gross additions on `+` lines. Removals are reported as a separate quantity, and net change as a secondary. Under a net metric a refactor that replaces ten `any` annotations with concrete types is indistinguishable from a PR that touched nothing.

---

## 7. Regex parser revision plan

**Implemented as of 2026-09-16** in `catalogue/`: `constructs.py` holds all 85 entries with their tier, failure mode, family, and pattern; `preprocess.py` does the diff parsing, comment and string stripping, and file filtering; `count.py` is the single counting entry point. `tests/test_catalogue.py` carries positive and negative cases for every ID and must pass before extraction runs. The sections below are the specification those modules implement.

No code changes until the catalogue above is signed off. When it is, the revision has five parts.

### 7.1 Preprocessing, shared across languages

1. Operate on added lines (`+`) and removed lines (`-`) separately; never on the concatenated patch.
2. Strip line comments and block comments before matching (`//`, `/* */`, `///`, `//!`, `#region`). Keep `// SAFETY:`, `// @ts-*`, and `#[allow]` by extracting them *before* stripping.
3. Strip string and template-literal contents (replace with `""`) so `"type": "any"` and HTML in strings never match.
4. File filter: `.ts`/`.tsx` (drop `.d.ts` for RQ1/RQ2 counts, keep for a separate ambient-declaration flag), `.cs` (drop `*.Designer.cs`, `*.g.cs`, `*.generated.cs`), `.rs` (drop `target/`, `*.pb.rs`, files under `tests/` and `benches/` for RS-E6 only). Plus `tsconfig*.json`, `*.csproj`, `Directory.Build.props` for TS-E9/CS-E3.
5. Deduplicate PRs by `(repo, number)` before counting; the Table 1 to Table 3 discrepancy the reviewer found must be impossible by construction.

### 7.2 One regex per catalogue ID, with a test file

Each ID in Sections 3 to 5 gets exactly one compiled pattern, and a `tests/patterns/<lang>_<id>.txt` file with at least 10 positive and 10 negative lines, including the known false positives listed in the detection notes. The test suite runs before any extraction. This is what the reviewer meant by "validates the construct-counting tool through tests".

### 7.3 Occurrence-level manual validation

The earlier version of this section (300 matched lines plus 100 unmatched, per language) does not work. Spread over roughly 25 constructs it yields about 12 matches each, giving a Wilson interval near ±0.25, which cannot decide a 0.9 threshold. And 100 random unmatched lines will contain zero instances of rare constructs such as `transmute` or `satisfies`, so recall would be estimable for only the two or three most frequent. Precision and recall need separate designs.

**Precision.** Per construct, draw a random sample of 30 matched lines, or take a census where fewer than 30 matches exist. At roughly 25 constructs this is about 750 lines per language. Two annotators label each line with the correct catalogue ID or "none".

**Recall.** Draw 20 whole changed files per language at random and have both annotators mark every occurrence of every catalogue construct exhaustively. Exhaustive file annotation is the only design that surfaces what the regexes miss. Report recall per construct where the file sample contains at least 10 occurrences, and report "not estimable" otherwise rather than quoting a number from 2 instances.

Report Wilson 95% intervals throughout and Cohen's κ before consensus. Fix the decision rule before looking at results: a construct whose precision lower bound falls below 0.9 is reported as unreliable and excluded from statistical tests, but it stays in the catalogue with its measured precision attached. Recall below 0.8 is reported as a threat, not hidden. Constructs are never silently deleted after the data is seen. This replaces the current situation where only PR-level relevance was validated.

### 7.4 Output schema

Per PR: `{pr_key, language, group, agent, files_counted, lines_added, lines_removed, <ID>_add, <ID>_rem for every ID}`. Tier is a lookup table, not a column, so the analysis scripts can regroup without re-extracting.

### 7.5 Later, not now

If regex precision for CS-E7 (explicit cast), RS-E7 (indexing), or TS-E3 (angle-bracket assertions) cannot reach 0.9, move those three to tree-sitter queries. Everything else in the catalogue has a lexical signature and does not need an AST.

---

## 8. References

Grounding rule (Section 2.2): official documentation, an official linter rule, or a prior study is each sufficient on its own. Where a construct rests on documentation alone, the tables say so and the paper must say so too. Entries marked (bib) are already in `overleaf_writeup/references.bib`.

Constructs currently grounded on documentation and language-design papers only, with no usage study in the literature: C# `dynamic`, the C# null-forgiving operator, C# `unsafe`. This is a gap in the field rather than a defect in the catalogue, and it is an argument that the C# arm is a contribution.

1. G. Bierman, M. Abadi, M. Torgersen. Understanding TypeScript. ECOOP 2014. (bib: bierman2014)
2. Z. Gao, C. Bird, E. T. Barr. To Type or Not to Type: Quantifying Detectable Bugs in JavaScript. ICSE 2017. https://doi.org/10.1109/ICSE.2017.75
3. J. Bogner, M. Merkel. To Type or Not to Type? A Systematic Comparison of the Software Quality of JavaScript and TypeScript Applications on GitHub. MSR 2022. (bib: bogner2022type) https://arxiv.org/abs/2203.11115
4. D. Vanderkam. The Seven Sources of Unsoundness in TypeScript. 2021. https://effectivetypescript.com/2021/05/06/unsoundness/ (grey literature by the author of [5]; use to structure the argument, cite [1] and [15] for the formal claim)
5. D. Vanderkam. Effective TypeScript, 2nd ed. O'Reilly 2024. (bib: vanderkam2024effective)
6. G. Bierman, E. Meijer, M. Torgersen. Adding Dynamic Types to C#. ECOOP 2010. (bib: bierman2010adding)
7. L. Fischer, S. Hanenberg. An Empirical Investigation of the Effects of Type Systems and Code Completion on API Usability Using TypeScript and JavaScript in MS Visual Studio. DLS 2015. (bib: fischer2015empirical)
8. V. Astrauskas, C. Matheja, F. Poli, P. Müller, A. J. Summers. How Do Programmers Use Unsafe Rust? OOPSLA 2020. https://doi.org/10.1145/3428204
9. A. N. Evans, B. Campbell, M. L. Soffa. Is Rust Used Safely by Software Developers? ICSE 2020. (bib)
10. B. Qin, Y. Chen, Z. Yu, L. Song, Y. Zhang. Understanding Memory and Thread Safety Practices and Issues in Real-World Rust Programs. PLDI 2020. https://doi.org/10.1145/3385412.3385204
11. H. Xu, Z. Chen, M. Sun, Y. Zhou, M. R. Lyu. Memory-Safety Challenge Considered Solved? An In-Depth Study with All Rust CVEs. TOSEM 2021. https://doi.org/10.1145/3466642
12. M. Cui, S. Sun, H. Xu, Y. Zhou. Is unsafe an Achilles' Heel? A Comprehensive Study of Safety Requirements in Unsafe Rust Programming. ICSE 2024, pages 106:1-106:13. https://doi.org/10.1145/3597503.3639136 (verified 2026-09-16)
13. B. Qin, Y. Chen, H. Liu, H. Zhang, Q. Wen, L. Song, Y. Zhang. Understanding and Detecting Real-World Safety Issues in Rust. IEEE TSE 2024. https://songlh.github.io/paper/rust-tse.pdf (verify author list against the published version before citing)
14. PanicFI: An Infrastructure for Fixing Panic Bugs in Real-World Rust Programs. arXiv 2408.03262, 2024. (verify authors and venue before citing)
15. A. Rastogi, N. Swamy, C. Fournet, G. Bierman, P. Vekris. Safe & Efficient Gradual Typing for TypeScript. POPL 2015. https://doi.org/10.1145/2676726.2676971
16. G. Mezzetti, A. Møller, F. Strocco. Type Unsoundness in Practice: An Empirical Study of Dart. Proceedings of the 12th Symposium on Dynamic Languages (DLS) 2016. https://cs.au.dk/~amoeller/papers/undart/paper.pdf (verified 2026-09-16; methodological template, an empirical study of how often unsound features are exercised)
17. J. G. Siek, W. Taha. Gradual Typing for Functional Languages. Scheme and Functional Programming Workshop 2006. (theory of the `any`-style dynamic type)
18. A. Takikawa, D. Feltey, B. Greenman, M. S. New, J. Vitek, M. Felleisen. Is Sound Gradual Typing Dead? POPL 2016. (why unchecked boundaries are the pragmatic choice TS and C# made)
19. K. R. Fulton, A. Chan, D. Votipka, M. Hicks, M. L. Mazurek. Benefits and Drawbacks of Adopting a Secure Programming Language: Rust as a Case Study. SOUPS 2021.
20. S. Zhu, Z. Zhang, B. Qin, A. Xiong, L. Song. Learning and Programming Challenges of Rust: A Mixed-Methods Study. ICSE 2022. (developer motivation for reaching for `unwrap` and `clone`)
21. E. K. Kristensen, A. Møller. Type Test Scripts for TypeScript Testing. OOPSLA 2017. https://doi.org/10.1145/3133914 (evidence that hand-written declaration files contain dozens of real type errors; supports the `.d.ts` decision in Section 9)
22. E. K. Kristensen, A. Møller. Inference and Evolution of TypeScript Declaration Files. FASE 2017.

Official documentation (cite as web references with access date 2026-09-14):

- TypeScript Handbook: Everyday Types; Narrowing; More on Functions; Object Types; Type Manipulation. https://www.typescriptlang.org/docs/handbook/
- TypeScript release notes 2.0, 2.6, 3.0, 3.4, 3.7, 3.9, 4.9. https://www.typescriptlang.org/docs/handbook/release-notes/
- typescript-eslint rules: `no-explicit-any`, `no-non-null-assertion`, `ban-ts-comment`, `no-unsafe-type-assertion`, `consistent-type-assertions`, `no-unsafe-function-type`, `no-empty-object-type`. https://typescript-eslint.io/rules/
- Microsoft Learn, C# reference: Built-in reference types (`dynamic`); Nullable reference types; `!` (null-forgiving) operator; Type-testing operators and cast expressions; Unsafe code, pointer types, and function pointers; `#pragma warning`; Pattern matching. https://learn.microsoft.com/en-us/dotnet/csharp/
- dotnet/csharplang, Nullable reference types specification (C# 8.0). https://github.com/dotnet/csharplang/blob/main/proposals/csharp-8.0/nullable-reference-types-specification.md
- The Rust Programming Language, ch. 9, 10, 15.5, 20.1. https://doc.rust-lang.org/book/
- The Rust Reference: Type cast expressions; Unsafety; Lint check attributes. https://doc.rust-lang.org/reference/
- The Rustonomicon: Transmutes. https://doc.rust-lang.org/nomicon/transmutes.html
- rust-clippy lint list: `unwrap_used`, `expect_used`, `as_conversions`, `cast_possible_truncation`, `indexing_slicing`, `undocumented_unsafe_blocks`, `panic`, `todo`, `unimplemented`, `unreachable`. https://rust-lang.github.io/rust-clippy/master/

---

## 9. Open decisions for Abram and Imgyeong

1. Tier B in RQ2 or in RQ1? Proposal: RQ2 reports Tier A as the headline and Tier B as a labelled secondary panel; RQ1 covers Tier C and D.
2. Keep C# `var` out entirely, or report it descriptively? Proposal: out.
3. Whether to count `.d.ts` files at all.
4. Whether the `.tsx` angle-bracket assertion exclusion is acceptable, given that it under-counts TS-E3 in React code.
5. Whether to drop RS-E7 (slice indexing), CS-E9 (boxing to `object`), and CS-E10 (reflection). Recommendation: drop all three. Indexing waives a bounds check rather than a type check, `object` is the fully checked top type so the escape is the cast back out (already CS-E7), and reflection will not reach acceptable regex precision against delegates and events.
6. Whether the TypeScript empty object type and `Object` stay under TS-E6. Recommendation: keep `Function`, which really does return `any` when called, and drop the other two, since `{}` means "anything non-nullish" and member access on it is still checked.
7. **Freeze the catalogue before extraction runs.** Once items 1 to 6 are settled, commit this file with a timestamp and include it in the replication package. If the catalogue can still change after the counts are seen, the study is post-hoc. Validation may mark a construct unreliable, never remove it.
