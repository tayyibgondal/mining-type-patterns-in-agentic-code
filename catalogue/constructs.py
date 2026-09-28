"""The construct catalogue: one definition, used by every stage.

This module is the single source of truth for what a "type pattern" and an
"escape hatch" are in this study. Before it existed the repository carried six
drifted copies of the feature lists plus six more regexes inlined in a figure
script, and no two agreed.

Every entry is grounded in `docs/type_patterns_and_escape_hatches.md`, which
records the documentation quote, the linter rule, and the prior study behind
each classification. The IDs here (TS-E1, CS-E7, RS-E5 ...) are the IDs in that
document; do not renumber them.

Two orthogonal axes, never collapsed into one score:

  tier          A  the compile-time guarantee is waived, nothing replaces it
                B  the guarantee is relocated to a runtime check
                C  expressiveness, adds or refines type information
                D  safety-enhancing, restores or strengthens a guarantee

  failure_mode  none         types erased, nothing happens at runtime
                silent       a wrong value, no diagnostic
                silent-lossy a defined but truncated or saturated value
                undefined    undefined behaviour
                loud         exception or panic at the point of failure

Tier A and Tier B counts are never summed. Families are reported separately:
`escape` and `suppression` answer RQ2, `expressiveness` and `safety` answer RQ1.

`reliable=False` marks a construct whose regex cannot be trusted to the 0.9
precision bar without occurrence-level validation. Such constructs stay in the
catalogue and are reported with their measured precision, but are excluded from
the statistical tests. They are never silently dropped.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Iterator

LANGUAGES = ("TypeScript", "C#", "Rust")

FAMILIES = ("escape", "suppression", "expressiveness", "safety")
TIERS = ("A", "B", "C", "D")
FAILURE_MODES = ("none", "silent", "silent-lossy", "undefined", "loud", "n/a")


@dataclass(frozen=True)
class Construct:
    """One catalogue entry."""

    id: str                      # "TS-E1", the ID in the taxonomy document
    language: str
    key: str                     # stable column stem: key_add / key_rem
    display_name: str            # figure label
    family: str
    tier: str
    failure_mode: str
    pattern: str                 # counted with re.findall over prepared lines
    evidence: str                # D / L / P codes, see the taxonomy document
    reliable: bool = True        # False -> reported, excluded from tests
    scope: str = "line"          # "line" per occurrence, "pr_flag" once per PR
    line_exclude: str | None = None   # skip this line for this construct

    _rx: re.Pattern = field(init=False, repr=False, compare=False, default=None)
    _rx_exclude: re.Pattern = field(init=False, repr=False, compare=False,
                                    default=None)

    def __post_init__(self) -> None:
        object.__setattr__(self, "_rx", re.compile(self.pattern))
        object.__setattr__(
            self, "_rx_exclude",
            re.compile(self.line_exclude) if self.line_exclude else None)

    def count_line(self, line: str) -> int:
        """Occurrences on one already-preprocessed line."""
        if self._rx_exclude is not None and self._rx_exclude.search(line):
            return 0
        return len(self._rx.findall(line))

    @property
    def add_col(self) -> str:
        return f"{self.key}_add"

    @property
    def rem_col(self) -> str:
        return f"{self.key}_rem"


# Shared sub-patterns -------------------------------------------------------

# `!` used as an assertion, not as logical negation and not as part of `!=`.
# Requires an identifier, `)` or `]` immediately before, and a member-access or
# statement-terminating character after. `a !== b` and `!(cond)` do not match.
BANG_ASSERTION = r"(?<=[\w$\)\]])!(?=\s*[.\[\(;,\)\}]|\s*$)"


# --------------------------------------------------------------------------
# TypeScript
# --------------------------------------------------------------------------

TYPESCRIPT: tuple[Construct, ...] = (
    # --- escape hatches ---------------------------------------------------
    Construct(
        id="TS-E1", language="TypeScript", key="any", display_name="any",
        family="escape", tier="A", failure_mode="none",
        # `: any`, `as any`, `<any>` or `, any>` in type arguments, `any[]`.
        # `\b` after `any` keeps `anything` and `anyOf` out.
        pattern=r"(?::\s*any\b)|(?:\bas\s+any\b)|(?:[<,]\s*any\s*(?=[,>]))"
                r"|(?:\bany\s*\[\s*\])",
        evidence="D Handbook Everyday Types; L no-explicit-any; P [1][2][3]"),
    Construct(
        id="TS-E2", language="TypeScript", key="double_assertion",
        display_name="double assertion",
        family="escape", tier="A", failure_mode="none",
        pattern=r"\bas\s+(?:unknown|any)\s+as\b",
        evidence="D Handbook Everyday Types; P [1][4]"),
    Construct(
        id="TS-E3", language="TypeScript", key="type_assertion",
        display_name="type assertion",
        family="escape", tier="A", failure_mode="none",
        # `x as T`. `as const` is Tier D, double assertions are TS-E2.
        pattern=r"\bas\s+(?!const\b)(?!unknown\s+as\b)(?!any\s+as\b)"
                r"(?:[A-Z_$][\w$]*|string|number|boolean|bigint|symbol"
                r"|object|void|never|null|undefined)\b",
        # import/export aliasing and mapped-type key remapping also use `as`.
        # A double assertion ends in `as T`, which this pattern would also
        # match; TS-E2 counts those lines instead.
        line_exclude=r"^\s*(?:import|export)\b|\[[^\]]*\bin\s+keyof\b"
                     r"|\bas\s+(?:unknown|any)\s+as\b",
        evidence="D Handbook Everyday Types; L no-unsafe-type-assertion; P [4]"),
    Construct(
        id="TS-E4", language="TypeScript", key="non_null_assertion",
        display_name="non-null assertion (!)",
        family="escape", tier="A", failure_mode="none",
        pattern=BANG_ASSERTION,
        evidence="D Handbook Everyday Types, rel. 2.0; L no-non-null-assertion"),
    Construct(
        id="TS-E5", language="TypeScript", key="ts_ignore",
        display_name="@ts-ignore",
        family="suppression", tier="A", failure_mode="none",
        pattern=r"@ts-ignore\b",
        evidence="D rel. 2.6; L ban-ts-comment"),
    Construct(
        id="TS-E5b", language="TypeScript", key="ts_expect_error",
        display_name="@ts-expect-error",
        family="suppression", tier="A", failure_mode="none",
        pattern=r"@ts-expect-error\b",
        evidence="D rel. 3.9; L ban-ts-comment"),
    Construct(
        id="TS-E5c", language="TypeScript", key="ts_nocheck",
        display_name="@ts-nocheck",
        family="suppression", tier="A", failure_mode="none",
        pattern=r"@ts-nocheck\b",
        evidence="D rel. 3.7; L ban-ts-comment"),
    Construct(
        id="TS-E6", language="TypeScript", key="function_type",
        display_name="Function type",
        family="escape", tier="A", failure_mode="none",
        pattern=r"(?::\s*Function\b)|(?:[<,]\s*Function\s*(?=[,>]))",
        evidence="D Handbook More on Functions; L no-unsafe-function-type"),
    Construct(
        id="TS-E7", language="TypeScript", key="any_index_signature",
        display_name="index signature: any",
        family="escape", tier="A", failure_mode="none",
        pattern=r"\[\s*\w+\s*:\s*(?:string|number|symbol)\s*\]\s*:\s*any\b",
        evidence="D Handbook Object Types; special case of TS-E1"),
    Construct(
        id="TS-E8", language="TypeScript", key="type_predicate",
        display_name="type predicate (x is T)",
        family="escape", tier="B", failure_mode="silent",
        pattern=r"(?::\s*\w+\s+is\s+[A-Z_$][\w$]*)|(?:\basserts\s+\w+\s+is\b)",
        evidence="D Handbook Narrowing; P [4]"),
    Construct(
        id="TS-E9", language="TypeScript", key="strictness_optout",
        display_name="strictness opt-out (tsconfig)",
        family="suppression", tier="A", failure_mode="none",
        scope="pr_flag",
        pattern=r'"(?:strict|noImplicitAny|strictNullChecks|strictFunctionTypes'
                r'|strictPropertyInitialization|strictBindCallApply)"\s*:\s*false',
        evidence="D tsconfig reference"),

    # --- safety-enhancing -------------------------------------------------
    Construct(
        id="TS-D1", language="TypeScript", key="unknown_type",
        display_name="unknown",
        family="safety", tier="D", failure_mode="n/a",
        pattern=r"(?::\s*unknown\b)|(?:\bas\s+unknown\b(?!\s+as))"
                r"|(?:[<,]\s*unknown\s*(?=[,>]))",
        evidence="D rel. 3.0, the type-safe counterpart of any"),
    Construct(
        id="TS-D2", language="TypeScript", key="satisfies",
        display_name="satisfies",
        family="safety", tier="D", failure_mode="n/a",
        pattern=r"\bsatisfies\s+[A-Za-z_$\{\[]",
        evidence="D rel. 4.9"),
    Construct(
        id="TS-D3", language="TypeScript", key="as_const",
        display_name="as const",
        family="safety", tier="D", failure_mode="n/a",
        pattern=r"\bas\s+const\b",
        evidence="D rel. 3.4, const assertions"),
    Construct(
        id="TS-D4", language="TypeScript", key="readonly",
        display_name="readonly",
        family="safety", tier="D", failure_mode="n/a",
        pattern=r"(?:\breadonly\s+(?:[A-Za-z_$][\w$]*|\[))|(?:\bReadonly\s*<)",
        evidence="D Handbook Object Types"),
    Construct(
        # The safe counterpart of TS-E4: handles absence instead of asserting
        # it away. Reported opposite `!` so the contrast is visible.
        id="TS-D6", language="TypeScript", key="optional_chaining",
        display_name="optional chaining (?.)",
        family="safety", tier="D", failure_mode="n/a",
        pattern=r"\?\.(?![\d])",
        evidence="D rel. 3.7, optional chaining"),
    Construct(
        id="TS-D7", language="TypeScript", key="nullish_coalescing",
        display_name="nullish coalescing (??)",
        family="safety", tier="D", failure_mode="n/a",
        pattern=r"\?\?(?!=)",
        evidence="D rel. 3.7, nullish coalescing"),

    # --- expressiveness ---------------------------------------------------
    Construct(
        id="TS-C1", language="TypeScript", key="generics",
        display_name="generics",
        family="expressiveness", tier="C", failure_mode="n/a",
        pattern=r"\b(?:interface|type|class|function|declare\s+function"
                r"|const\s+\w+\s*:\s*)\s*\w*\s*<[^<>]+>",
        evidence="D Handbook Type Manipulation, Generics"),
    Construct(
        id="TS-C2", language="TypeScript", key="conditional_types",
        display_name="conditional types",
        family="expressiveness", tier="C", failure_mode="n/a",
        pattern=r"\bextends\b[^?\n]{0,120}\?[^:\n]{0,120}:",
        evidence="D Handbook Conditional Types"),
    Construct(
        id="TS-C3", language="TypeScript", key="infer",
        display_name="infer",
        family="expressiveness", tier="C", failure_mode="n/a",
        pattern=r"\binfer\s+[A-Z_$][\w$]*",
        evidence="D Handbook Conditional Types"),
    Construct(
        id="TS-C4", language="TypeScript", key="mapped_types",
        display_name="mapped types",
        family="expressiveness", tier="C", failure_mode="n/a",
        pattern=r"\[\s*(?:readonly\s+)?[A-Za-z_$][\w$]*\s+in\s+",
        evidence="D Handbook Mapped Types"),
    Construct(
        id="TS-C5", language="TypeScript", key="key_remapping",
        display_name="key remapping",
        family="expressiveness", tier="C", failure_mode="n/a",
        pattern=r"\[[^\]]*\bin\b[^\]]*\bas\s+",
        evidence="D Handbook Mapped Types, key remapping via as"),
    Construct(
        id="TS-C6", language="TypeScript", key="template_literal_types",
        display_name="template literal types",
        family="expressiveness", tier="C", failure_mode="n/a",
        # Read from the raw line: stripping blanks backtick contents. A
        # type-position template literal cannot be told from a runtime
        # template string by regex, hence reliable=False.
        pattern=r"(?:[=:|]\s*)`[^`\n]*\$\{[^}\n]+\}[^`\n]*`",
        evidence="D Handbook Template Literal Types",
        # A template literal in a type position cannot be told from a runtime
        # template string by regex alone.
        reliable=False),
    Construct(
        id="TS-C7", language="TypeScript", key="keyof",
        display_name="keyof",
        family="expressiveness", tier="C", failure_mode="n/a",
        pattern=r"\bkeyof\b",
        evidence="D Handbook Keyof Type Operator"),
    Construct(
        id="TS-C8", language="TypeScript", key="typeof_type",
        display_name="typeof (type position)",
        family="expressiveness", tier="C", failure_mode="n/a",
        pattern=r"(?::\s*typeof\s+)|(?:[<,]\s*typeof\s+)",
        evidence="D Handbook Typeof Type Operator"),
    Construct(
        id="TS-C9", language="TypeScript", key="indexed_access",
        display_name="indexed access types",
        family="expressiveness", tier="C", failure_mode="n/a",
        pattern=r"\w+\s*\[\s*keyof\s+\w+\s*\]",
        evidence="D Handbook Indexed Access Types"),
    Construct(
        id="TS-C10", language="TypeScript", key="utility_types",
        display_name="utility types",
        family="expressiveness", tier="C", failure_mode="n/a",
        pattern=r"\b(?:Partial|Required|Readonly|Pick|Omit|Record|ReturnType"
                r"|InstanceType|Parameters|ConstructorParameters|Awaited"
                r"|ThisType|Exclude|Extract|NonNullable)\s*<",
        evidence="D Handbook Utility Types"),
    Construct(
        id="TS-C11", language="TypeScript", key="union_types",
        display_name="union types",
        family="expressiveness", tier="C", failure_mode="n/a",
        # `||` cannot match because the second `|` is not in the trailing class.
        # Bitwise or in expression position still can, hence reliable=False.
        pattern=r"[A-Za-z0-9_$)\]'\"]\s*\|\s*[A-Za-z0-9_$(\['\"]",
        evidence="D Handbook Everyday Types, union types",
        reliable=False),
    Construct(
        id="TS-C12", language="TypeScript", key="intersection_types",
        display_name="intersection types",
        family="expressiveness", tier="C", failure_mode="n/a",
        pattern=r"[A-Za-z0-9_$)\]]\s*&\s*(?!&)[A-Za-z0-9_$(\[]",
        evidence="D Handbook Object Types, intersection types",
        reliable=False),
    Construct(
        id="TS-C13", language="TypeScript", key="discriminated_union",
        display_name="discriminated union tag",
        family="expressiveness", tier="C", failure_mode="n/a",
        pattern=r"\b(?:kind|type|tag|_tag|variant)\s*:\s*['\"][A-Za-z_0-9]*['\"]",
        evidence="D Handbook Narrowing, discriminated unions",
        reliable=False),
    Construct(
        id="TS-C14", language="TypeScript", key="optional_property",
        display_name="optional property",
        family="expressiveness", tier="C", failure_mode="n/a",
        pattern=r"\w+\s*\?\s*:(?!:)",
        evidence="D Handbook Object Types, optional properties"),
    Construct(
        id="TS-C15", language="TypeScript", key="enum_type",
        display_name="enum",
        family="expressiveness", tier="C", failure_mode="n/a",
        pattern=r"\b(?:const\s+)?enum\s+[A-Z_$][\w$]*",
        evidence="D Handbook Enums"),
)


# --------------------------------------------------------------------------
# C#
# --------------------------------------------------------------------------

CSHARP: tuple[Construct, ...] = (
    # --- escape hatches ---------------------------------------------------
    Construct(
        id="CS-E1", language="C#", key="dynamic", display_name="dynamic",
        family="escape", tier="B", failure_mode="loud",
        pattern=r"(?:\bdynamic\s+[A-Za-z_@]\w*)|(?:\(\s*dynamic\s*\))"
                r"|(?:[<,]\s*dynamic\s*(?=[,>]))|(?:\bdynamic\s*\[\s*\])"
                r"|(?:\bas\s+dynamic\b)",
        line_exclude=r"\[\s*Dynamic|DynamicAttribute",
        evidence="D MS Learn Built-in reference types; P [6][7]"),
    Construct(
        id="CS-E2", language="C#", key="null_forgiving",
        display_name="null-forgiving (!)",
        family="escape", tier="A", failure_mode="none",
        pattern=BANG_ASSERTION,
        evidence="D MS Learn ! (null-forgiving) operator; L CS8600-CS8625"),
    Construct(
        id="CS-E3", language="C#", key="nullable_disable",
        display_name="#nullable disable",
        family="suppression", tier="A", failure_mode="none",
        pattern=r"(?:#nullable\s+(?:disable|restore)\b)"
                r"|(?:<Nullable>\s*disable\s*</Nullable>)",
        evidence="D MS Learn Nullable reference types, nullable context"),
    Construct(
        id="CS-E4", language="C#", key="warning_suppression",
        display_name="warning suppression",
        family="suppression", tier="A", failure_mode="none",
        pattern=r"(?:#pragma\s+warning\s+disable\b)"
                r"|(?:\[\s*(?:System\.Diagnostics\.CodeAnalysis\.)?"
                r"SuppressMessage\s*\()",
        evidence="D MS Learn #pragma warning; code-analysis suppression"),
    Construct(
        id="CS-E5", language="C#", key="unsafe", display_name="unsafe",
        family="escape", tier="A", failure_mode="undefined",
        pattern=r"(?:\bunsafe\b)|(?:\bfixed\s*\()|(?:\bstackalloc\b)"
                r"|(?:\bdelegate\s*\*)",
        evidence="D MS Learn Unsafe code, pointer types, function pointers"),
    Construct(
        id="CS-E6", language="C#", key="unchecked_reinterpret",
        display_name="Unsafe.As / MemoryMarshal",
        family="escape", tier="A", failure_mode="undefined",
        pattern=r"(?:\bUnsafe\s*\.\s*(?:As|AsRef|AsPointer|Read|Write)\b)"
                r"|(?:\bMemoryMarshal\s*\.\s*(?:Cast|AsRef|GetReference)\b)",
        evidence="D System.Runtime.CompilerServices.Unsafe API docs"),
    Construct(
        id="CS-E7", language="C#", key="explicit_cast",
        display_name="explicit cast (T)x",
        family="escape", tier="B", failure_mode="loud",
        pattern=r"\(\s*(?:[A-Z][\w.]*(?:<[^<>()]*>)?(?:\[\s*\])?)\s*\)"
                r"\s*(?=[A-Za-z_@(])",
        # Distinguishing a cast from a method call with one capitalised
        # argument needs a parser. Validated in Phase 4 before use in tests.
        reliable=False,
        evidence="D MS Learn Type-testing operators and cast expressions"),
    Construct(
        id="CS-E8", language="C#", key="as_operator",
        display_name="as operator",
        family="escape", tier="B", failure_mode="silent",
        pattern=r"\bas\s+(?!dynamic\b)[A-Z_][\w.]*(?:<[^<>]*>)?(?:\[\s*\])?",
        line_exclude=r"^\s*using\b",
        evidence="D MS Learn Type-testing operators and cast expressions"),
    Construct(
        id="CS-E9", language="C#", key="object_type",
        display_name="object as declared type",
        family="escape", tier="B", failure_mode="loud",
        pattern=r"(?::\s*object\b)|(?:\bobject\s+[A-Za-z_@]\w*\s*[=;,\)])"
                r"|(?:[<,]\s*object\s*(?=[,>]))",
        reliable=False,
        evidence="D MS Learn Boxing and unboxing"),
    Construct(
        id="CS-E10", language="C#", key="reflection",
        display_name="reflection invocation",
        family="escape", tier="B", failure_mode="loud",
        pattern=r"(?:\.\s*GetMethod\s*\()|(?:\.\s*Invoke\s*\()"
                r"|(?:\bActivator\s*\.\s*CreateInstance\b)"
                r"|(?:\bType\s*\.\s*GetType\s*\()",
        reliable=False,
        evidence="D MS Learn reflection"),

    # --- safety-enhancing -------------------------------------------------
    Construct(
        id="CS-D1", language="C#", key="nullable_enable",
        display_name="#nullable enable",
        family="safety", tier="D", failure_mode="n/a",
        pattern=r"(?:#nullable\s+enable\b)|(?:<Nullable>\s*enable\s*</Nullable>)",
        evidence="D MS Learn Nullable reference types"),
    Construct(
        id="CS-D2", language="C#", key="nullable_annotation",
        display_name="nullable annotation (T?)",
        family="safety", tier="D", failure_mode="n/a",
        pattern=r"\b(?:string|object|[A-Z][\w.]*)\?(?=\s+[A-Za-z_@]|\s*[,>\)])",
        evidence="D MS Learn Nullable reference types"),
    Construct(
        id="CS-D3", language="C#", key="pattern_type_test",
        display_name="pattern type test (is T x)",
        family="safety", tier="D", failure_mode="n/a",
        pattern=r"\bis\s+(?:not\s+)?(?:null\b|[A-Z][\w.]*(?:\s+[a-z_]\w*)?)",
        evidence="D MS Learn Pattern matching"),
    Construct(
        id="CS-D4", language="C#", key="construction_invariants",
        display_name="record / init / required",
        family="safety", tier="D", failure_mode="n/a",
        pattern=r"(?:\brecord\s+(?:class\s+|struct\s+)?[A-Z]\w*)"
                r"|(?:\binit\s*[;{])|(?:\brequired\s+[A-Za-z_@])",
        evidence="D MS Learn C# 9 records, C# 11 required members"),
    Construct(
        id="CS-D5", language="C#", key="generic_constraint",
        display_name="generic constraint (where)",
        family="safety", tier="D", failure_mode="n/a",
        pattern=r"\bwhere\s+\w+\s*:\s*",
        evidence="D MS Learn Constraints on type parameters"),

    # --- expressiveness ---------------------------------------------------
    Construct(
        id="CS-C1", language="C#", key="generics", display_name="generics",
        family="expressiveness", tier="C", failure_mode="n/a",
        # Declarations only. The old `<[^<>]+>` matched every generic use and
        # every HTML tag that appeared inside a string literal.
        pattern=r"\b(?:class|interface|struct|record|delegate)\s+\w+\s*<[^<>]+>",
        evidence="D MS Learn Generics"),
    Construct(
        id="CS-C2", language="C#", key="variance", display_name="variance",
        family="expressiveness", tier="C", failure_mode="n/a",
        pattern=r"<\s*(?:in|out)\s+\w+",
        evidence="D MS Learn Covariance and contravariance"),
    Construct(
        id="CS-C3", language="C#", key="tuple", display_name="tuple",
        family="expressiveness", tier="C", failure_mode="n/a",
        pattern=r"\(\s*[A-Za-z_][\w.<>\[\]]*\s+[a-z_]\w*\s*,"
                r"\s*[A-Za-z_][\w.<>\[\]]*\s+[a-z_]\w*\s*\)",
        evidence="D MS Learn Tuple types"),
    Construct(
        id="CS-C4", language="C#", key="type_alias", display_name="type alias",
        family="expressiveness", tier="C", failure_mode="n/a",
        pattern=r"\busing\s+\w+\s*=\s*[\w<>,\s\[\].]+;",
        evidence="D MS Learn using alias directive"),
    Construct(
        id="CS-C5", language="C#", key="readonly_ref_struct",
        display_name="readonly / ref struct",
        family="expressiveness", tier="C", failure_mode="n/a",
        pattern=r"\b(?:readonly\s+struct|ref\s+struct|ref\s+readonly)\b",
        evidence="D MS Learn ref struct, readonly struct"),
)


# --------------------------------------------------------------------------
# Rust
# --------------------------------------------------------------------------

RUST: tuple[Construct, ...] = (
    # --- escape hatches ---------------------------------------------------
    Construct(
        id="RS-E1", language="Rust", key="unsafe_block",
        display_name="unsafe block",
        family="escape", tier="A", failure_mode="undefined",
        pattern=r"\bunsafe\s*\{",
        evidence="D Book ch. 20.1; L undocumented_unsafe_blocks; P [8]-[12]"),
    Construct(
        id="RS-E1b", language="Rust", key="unsafe_fn",
        display_name="unsafe fn",
        family="escape", tier="A", failure_mode="undefined",
        pattern=r"\bunsafe\s+(?:extern\s+\"[^\"]*\"\s+)?fn\b",
        evidence="D Book ch. 20.1"),
    Construct(
        id="RS-E1c", language="Rust", key="unsafe_impl",
        display_name="unsafe impl",
        family="escape", tier="A", failure_mode="undefined",
        pattern=r"\bunsafe\s+impl\b",
        evidence="D Book ch. 20.1; P [8][10]"),
    Construct(
        # Singled out by Astrauskas et al. and Qin et al. as the pattern where
        # hand-written soundness arguments most often fail. Previously buried
        # inside the aggregate unsafe count.
        id="RS-E1d", language="Rust", key="unsafe_impl_send_sync",
        display_name="unsafe impl Send/Sync",
        family="escape", tier="A", failure_mode="undefined",
        pattern=r"\bunsafe\s+impl(?:\s*<[^<>]*>)?\s+(?:Send|Sync)\b",
        evidence="D Book ch. 20.1; P [8][10]"),
    Construct(
        id="RS-E1e", language="Rust", key="unsafe_trait",
        display_name="unsafe trait",
        family="escape", tier="A", failure_mode="undefined",
        pattern=r"\bunsafe\s+trait\b",
        evidence="D Book ch. 20.1"),
    Construct(
        id="RS-E1f", language="Rust", key="unsafe_any",
        display_name="unsafe (any form)",
        family="escape", tier="A", failure_mode="undefined",
        pattern=r"\bunsafe\b",
        evidence="D Book ch. 20.1; the headline RQ2 metric for Rust"),
    Construct(
        id="RS-E2", language="Rust", key="transmute",
        display_name="transmute",
        family="escape", tier="A", failure_mode="undefined",
        pattern=r"(?:\bmem::transmute\b)|(?:\btransmute(?:_copy)?\s*(?:::\s*<|\())"
                r"|(?:\bfrom_raw_parts(?:_mut)?\s*\()",
        evidence="D Rustonomicon Transmutes; L wrong_transmute; P [10][11]"),
    Construct(
        id="RS-E3", language="Rust", key="allow_lint",
        display_name="#[allow(...)]",
        family="suppression", tier="A", failure_mode="none",
        pattern=r"#!?\[\s*allow\s*\(",
        evidence="D Rust Reference, lint check attributes"),
    Construct(
        id="RS-E4", language="Rust", key="unchecked_api",
        display_name="_unchecked APIs",
        family="escape", tier="A", failure_mode="undefined",
        pattern=r"(?:\.\s*(?:get_unchecked(?:_mut)?|unwrap_unchecked"
                r"|assume_init)\s*\()"
                r"|(?:\b(?:from_utf8_unchecked|unreachable_unchecked)\s*\()",
        evidence="D std docs, each marked unsafe fn"),
    Construct(
        id="RS-E5", language="Rust", key="unwrap_expect",
        display_name=".unwrap() / .expect()",
        family="escape", tier="B", failure_mode="loud",
        # unwrap_or / unwrap_or_else / unwrap_or_default are Tier D handling
        # and are excluded by requiring `(` straight after the method name.
        pattern=r"\.\s*(?:unwrap|expect|unwrap_err|expect_err)\s*\(",
        evidence="D Book ch. 9.2-9.3; L unwrap_used, expect_used; P [13][14]"),
    Construct(
        id="RS-E6", language="Rust", key="panic_macro",
        display_name="panic! / todo! / unreachable!",
        family="escape", tier="B", failure_mode="loud",
        pattern=r"\b(?:panic|unreachable|todo|unimplemented)\s*!\s*[\(\[\{]",
        evidence="D std macro docs; L panic, todo, unimplemented, unreachable"),
    Construct(
        id="RS-E7", language="Rust", key="direct_indexing",
        display_name="direct indexing",
        family="escape", tier="B", failure_mode="loud",
        pattern=r"[\w\)\]]\s*\[\s*[a-z_]\w*\s*\]",
        # Waives a bounds check rather than a type check, and the pattern
        # cannot be separated from array types or macros by regex.
        reliable=False,
        evidence="D std docs, indexing panics out of bounds; L indexing_slicing"),
    Construct(
        id="RS-E8", language="Rust", key="as_cast", display_name="as cast",
        family="escape", tier="A", failure_mode="silent-lossy",
        pattern=r"\bas\s+(?:[iu](?:8|16|32|64|128|size)|f32|f64|bool|char|str"
                r"|\*\s*(?:const|mut)\s|&)",
        evidence="D Rust Reference Type cast expressions; L as_conversions"),
    Construct(
        id="RS-E9", language="Rust", key="interior_mutability",
        display_name="RefCell / borrow_mut",
        family="escape", tier="B", failure_mode="loud",
        pattern=r"(?:\bRefCell\s*<)|(?:\bCell\s*<)|(?:\.\s*borrow(?:_mut)?\s*\()",
        evidence="D Book ch. 15.5, borrowing rules enforced at runtime"),
    Construct(
        id="RS-E10", language="Rust", key="dyn_any",
        display_name="dyn Any / downcast",
        family="escape", tier="B", failure_mode="loud",
        pattern=r"(?:\bdyn\s+Any\b)|(?:\.\s*downcast(?:_ref|_mut)?\s*::\s*<)",
        evidence="D std Any docs, downcasting is a runtime type test"),

    # --- safety-enhancing -------------------------------------------------
    Construct(
        id="RS-D1", language="Rust", key="question_operator",
        display_name="? operator",
        family="safety", tier="D", failure_mode="n/a",
        pattern=r"[\w\)\]]\?(?=\s*[;,\)\.\}]|\s*$)",
        evidence="D Book ch. 9.2, propagating errors"),
    Construct(
        id="RS-D2", language="Rust", key="checked_conversion",
        display_name="TryFrom / checked_*",
        family="safety", tier="D", failure_mode="n/a",
        pattern=r"(?:\bTryFrom\b)|(?:\bTryInto\b)|(?:\btry_from\s*\()"
                r"|(?:\.\s*try_into\s*\()"
                r"|(?:\.\s*checked_(?:add|sub|mul|div|rem|neg|pow)\s*\()",
        evidence="D std docs, fallible conversions"),
    Construct(
        id="RS-D3", language="Rust", key="safe_handling",
        display_name="safe Option/Result handling",
        family="safety", tier="D", failure_mode="n/a",
        pattern=r"(?:\.\s*(?:unwrap_or|unwrap_or_else|unwrap_or_default|ok_or"
                r"|ok_or_else|map_err|and_then)\s*\()"
                r"|(?:\b(?:if|while)\s+let\s+(?:Some|Ok|Err|None)\b)"
                r"|(?:\blet\s+(?:Some|Ok)\b[^;\n]*\belse\b)",
        evidence="D Book ch. 9"),
    Construct(
        id="RS-D4", language="Rust", key="lint_hardening",
        display_name="#[expect] / forbid(unsafe_code)",
        family="safety", tier="D", failure_mode="n/a",
        pattern=r"(?:#!?\[\s*expect\s*\()"
                r"|(?:#!?\[\s*(?:forbid|deny)\s*\(\s*unsafe_code)",
        evidence="D Rust Reference, lint check attributes"),
    Construct(
        # Extracted before comment stripping, see catalogue.preprocess.
        id="RS-D5", language="Rust", key="safety_comment",
        display_name="// SAFETY: comment",
        family="safety", tier="D", failure_mode="n/a",
        pattern=r"//[!/]?\s*SAFETY\s*:",
        evidence="L undocumented_unsafe_blocks; P [8]"),

    # --- expressiveness ---------------------------------------------------
    Construct(
        id="RS-C1", language="Rust", key="generics", display_name="generics",
        family="expressiveness", tier="C", failure_mode="n/a",
        pattern=r"(?:\b(?:fn|struct|enum|trait|type)\s+\w+\s*<\s*(?:'\w+\s*,\s*)?[A-Z]\w*)"
                r"|(?:\bimpl\s*<\s*(?:'\w+\s*,\s*)?[A-Z]\w*)",
        evidence="D Book ch. 10, generic data types"),
    Construct(
        id="RS-C2", language="Rust", key="lifetimes", display_name="lifetimes",
        family="expressiveness", tier="C", failure_mode="n/a",
        # A preceding `&`, `<`, `,` or `:` and no closing quote keeps char
        # literals such as 'a' out; the old pattern counted every one of them.
        pattern=r"[&<,:(]\s*'(?:static|[a-z_]\w*)\b(?!')",
        evidence="D Book ch. 10.3, lifetimes"),
    Construct(
        id="RS-C3", language="Rust", key="trait_bound",
        display_name="trait bound",
        family="expressiveness", tier="C", failure_mode="n/a",
        pattern=r"<[^<>]*\b\w+\s*:\s*[A-Z]\w*[^<>]*>",
        evidence="D Book ch. 10.2, trait bounds"),
    Construct(
        id="RS-C4", language="Rust", key="where_clause",
        display_name="where clause",
        family="expressiveness", tier="C", failure_mode="n/a",
        pattern=r"\bwhere\s+[\w']+\s*:",
        evidence="D Book ch. 10.2, where clauses"),
    Construct(
        id="RS-C5", language="Rust", key="impl_trait",
        display_name="impl Trait",
        family="expressiveness", tier="C", failure_mode="n/a",
        # Type position only. A bare `\bimpl\s+[A-Z]` also matches every trait
        # implementation (`impl Display for Foo`), which is a different thing.
        pattern=r"(?:->|:|\(|,|\+)\s*impl\s+[A-Z]\w*",
        evidence="D Book ch. 10.2, impl Trait in argument and return position"),
    Construct(
        id="RS-C6", language="Rust", key="dyn_trait",
        display_name="dyn Trait",
        family="expressiveness", tier="C", failure_mode="n/a",
        pattern=r"\bdyn\s+[A-Z]\w*",
        evidence="D Rust Reference, trait objects"),
    Construct(
        id="RS-C7", language="Rust", key="type_alias",
        display_name="type alias",
        family="expressiveness", tier="C", failure_mode="n/a",
        pattern=r"\btype\s+[A-Z]\w*\s*(?:<[^<>]*>)?\s*=",
        evidence="D Rust Reference, type aliases"),
    Construct(
        id="RS-C8", language="Rust", key="associated_type",
        display_name="associated type",
        family="expressiveness", tier="C", failure_mode="n/a",
        pattern=r"(?:\btype\s+[A-Z]\w*\s*(?::[^=;]*)?;)|(?:\bSelf::[A-Z]\w*)",
        evidence="D Book ch. 20.2, associated types"),
    Construct(
        id="RS-C9", language="Rust", key="phantom_data",
        display_name="PhantomData",
        family="expressiveness", tier="C", failure_mode="n/a",
        pattern=r"\bPhantomData\b",
        evidence="D Rustonomicon, PhantomData"),
    Construct(
        id="RS-C10", language="Rust", key="enum_def",
        display_name="enum definition",
        family="expressiveness", tier="C", failure_mode="n/a",
        pattern=r"\benum\s+[A-Z]\w*",
        evidence="D Book ch. 6, enums"),
    Construct(
        id="RS-C11", language="Rust", key="trait_def",
        display_name="trait definition",
        family="expressiveness", tier="C", failure_mode="n/a",
        pattern=r"\btrait\s+[A-Z]\w*",
        evidence="D Book ch. 10.2, traits"),
    Construct(
        id="RS-C12", language="Rust", key="send_sync",
        display_name="Send / Sync bound",
        family="expressiveness", tier="C", failure_mode="n/a",
        pattern=r"\b(?:Send|Sync)\b",
        evidence="D Book ch. 16.4, Send and Sync"),
    Construct(
        id="RS-C13", language="Rust", key="option_result",
        display_name="Option / Result",
        family="expressiveness", tier="C", failure_mode="n/a",
        pattern=r"\b(?:Option|Result)\s*<",
        evidence="D Book ch. 6.1 and ch. 9.2"),
)


# --------------------------------------------------------------------------
# Lookup helpers
# --------------------------------------------------------------------------

_BY_LANGUAGE: dict[str, tuple[Construct, ...]] = {
    "TypeScript": TYPESCRIPT,
    "C#": CSHARP,
    "Rust": RUST,
}

ALL: tuple[Construct, ...] = TYPESCRIPT + CSHARP + RUST

# The headline RQ2 metric per language. These share a row in the cross-language
# mapping (taxonomy Section 6), so they are comparable by the guarantee waived,
# not by surface syntax and not by risk.
HEADLINE_ESCAPE: dict[str, tuple[str, ...]] = {
    "TypeScript": ("any",),
    "C#": ("dynamic", "null_forgiving"),
    "Rust": ("unsafe_any",),
}

# Sub-counters that are subsets of a broader counter and must never be added to
# it, or to each other, when forming a total.
NESTED_KEYS: dict[str, tuple[str, ...]] = {
    "unsafe_any": ("unsafe_block", "unsafe_fn", "unsafe_impl",
                   "unsafe_impl_send_sync", "unsafe_trait"),
    "unsafe_impl": ("unsafe_impl_send_sync",),
    "any": ("any_index_signature",),
    # `x as unknown as T` matches the plain-assertion pattern too, so the
    # narrower counter is the child.
    "type_assertion": ("double_assertion",),
}


def constructs_for(language: str) -> tuple[Construct, ...]:
    try:
        return _BY_LANGUAGE[language]
    except KeyError:
        raise ValueError(
            f"unknown language {language!r}, expected one of {LANGUAGES}"
        ) from None


def by_family(language: str, family: str) -> tuple[Construct, ...]:
    return tuple(c for c in constructs_for(language) if c.family == family)


def by_tier(language: str, tier: str) -> tuple[Construct, ...]:
    return tuple(c for c in constructs_for(language) if c.tier == tier)


def get(construct_id: str) -> Construct:
    for c in ALL:
        if c.id == construct_id:
            return c
    raise KeyError(construct_id)


def get_by_key(language: str, key: str) -> Construct:
    for c in constructs_for(language):
        if c.key == key:
            return c
    raise KeyError(f"{language}:{key}")


def count_columns(language: str) -> list[str]:
    """Every count column an extractor writes for this language."""
    cols: list[str] = []
    for c in constructs_for(language):
        cols.extend((c.add_col, c.rem_col))
    return cols


def display_names(language: str) -> dict[str, str]:
    """key -> figure label, replacing the hardcoded map in _style.py."""
    return {c.key: c.display_name for c in constructs_for(language)}


def reliable_keys(language: str) -> list[str]:
    """Keys eligible for statistical testing before Phase 4 validation."""
    return [c.key for c in constructs_for(language) if c.reliable]


def iter_all() -> Iterator[Construct]:
    yield from ALL


def validate_catalogue() -> None:
    """Fail loudly on a malformed catalogue. Called by the test suite."""
    seen_ids: set[str] = set()
    for c in ALL:
        if c.id in seen_ids:
            raise ValueError(f"duplicate construct id {c.id}")
        seen_ids.add(c.id)
        if c.language not in LANGUAGES:
            raise ValueError(f"{c.id}: bad language {c.language!r}")
        if c.family not in FAMILIES:
            raise ValueError(f"{c.id}: bad family {c.family!r}")
        if c.tier not in TIERS:
            raise ValueError(f"{c.id}: bad tier {c.tier!r}")
        if c.failure_mode not in FAILURE_MODES:
            raise ValueError(f"{c.id}: bad failure_mode {c.failure_mode!r}")
        if c.scope not in ("line", "pr_flag"):
            raise ValueError(f"{c.id}: bad scope {c.scope!r}")
        # Tier C and D describe no failure; Tier A and B must name one.
        if c.tier in ("C", "D") and c.failure_mode != "n/a":
            raise ValueError(f"{c.id}: tier {c.tier} must have failure_mode n/a")
        if c.tier in ("A", "B") and c.failure_mode == "n/a":
            raise ValueError(f"{c.id}: tier {c.tier} needs a real failure_mode")
        if not c.evidence.strip():
            raise ValueError(f"{c.id}: missing evidence")
    for lang in LANGUAGES:
        keys = [c.key for c in constructs_for(lang)]
        dupes = {k for k in keys if keys.count(k) > 1}
        if dupes:
            raise ValueError(f"{lang}: duplicate keys {sorted(dupes)}")
        if not HEADLINE_ESCAPE.get(lang):
            raise ValueError(f"{lang}: no headline escape hatch declared")
        for key in HEADLINE_ESCAPE[lang]:
            get_by_key(lang, key)  # raises if absent


if __name__ == "__main__":
    validate_catalogue()
    for lang in LANGUAGES:
        cs = constructs_for(lang)
        fams = {f: len(by_family(lang, f)) for f in FAMILIES}
        unreliable = [c.id for c in cs if not c.reliable]
        print(f"{lang:<11} {len(cs):>3} constructs  {fams}")
        print(f"{'':<11} headline: {HEADLINE_ESCAPE[lang]}")
        print(f"{'':<11} needs validation before testing: {unreliable}")
    print(f"\ntotal: {len(ALL)} constructs across {len(LANGUAGES)} languages")
