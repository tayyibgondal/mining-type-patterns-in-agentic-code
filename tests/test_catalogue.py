"""Per-construct regex tests.

Section 7.2 of the taxonomy: every catalogue ID gets positive and negative
cases, and the negatives include the specific false positives named in that
document's detection notes. This suite is the gate before any extraction runs.

CASES maps a construct ID to (positives, negatives). A positive must produce at
least one match on a preprocessed line; a negative must produce none. Lines are
run through `catalogue.preprocess.strip_line` first, exactly as the counters
see them, so "the pattern is inside a string literal" is a legitimate negative.
"""
from __future__ import annotations

import pytest

from catalogue import constructs as K
from catalogue.count import needs_raw_text
from catalogue.preprocess import strip_line

# (positives, negatives) per construct ID
CASES: dict[str, tuple[list[str], list[str]]] = {
    # ---------------- TypeScript escape hatches ----------------
    "TS-E1": (
        ["let x: any;", "function f(): any {}", "const a: any[] = [];",
         "const b = x as any;", "Record<string, any>", "Map<K, any>",
         "function g(...args: any[]) {}", "let c: any = 1;"],
        ["let anything = 1;", "const anyOf = x;", "company: string;",
         'const s = "value: any";', "// returns any", "let a: unknown;",
         "anywhere(x);", "const manyItems = [];"],
    ),
    "TS-E2": (
        ["const a = x as unknown as Foo;", "return y as any as Bar;"],
        ["const a = x as Foo;", "const b = y as unknown;",
         "const c = z as const;"],
    ),
    "TS-E3": (
        ["const a = x as Foo;", "const b = y as string;",
         "return z as MyType;"],
        ["const a = x as const;", "import foo as bar from 'x';",
         "export { a as b };", "type T = { [K in keyof U as `x${K}`]: 1 };",
         "const c = y as unknown as Foo;"],
    ),
    "TS-E4": (
        ["const a = obj!.prop;", "const b = arr![0];", "fn!();",
         "this.thing!;", "foo()!.bar;"],
        ["if (!cond) return;", "if (!(a && b)) return;", "a !== b",
         "a != b", "const c = !flag;", "return !isValid(x);",
         "!function(){}()"],
    ),
    "TS-E5": (["// @ts-ignore", "  // @ts-ignore next line"],
              ["// ts-ignore is bad", "// @ts-expect-error"]),
    "TS-E5b": (["// @ts-expect-error", "/* @ts-expect-error */"],
               ["// @ts-ignore", "// expect error"]),
    "TS-E5c": (["// @ts-nocheck"], ["// @ts-ignore", "// nocheck"]),
    "TS-E6": (["let cb: Function;", "Map<string, Function>"],
              ["let f: () => void;", "function foo() {}",
               "class FunctionRegistry {}"]),
    "TS-E7": (["[key: string]: any;", "{ [k: number]: any }"],
              ["[key: string]: unknown;", "[key: string]: Foo;"]),
    "TS-E8": (["function isFoo(x: unknown): x is Foo {}",
               "function assertIt(v: unknown): asserts v is Bar {}"],
              ["function f(x: string): boolean {}", "const a = x is y;"]),
    "TS-E9": (['"strict": false,', '"noImplicitAny": false'],
              ['"strict": true,', '"target": "es2020"']),
    # ---------------- TypeScript safety ----------------
    "TS-D1": (["let x: unknown;", "const a = y as unknown;",
               "Map<string, unknown>"],
              ["let x: any;", "const b = y as unknown as Foo;",
               "const unknownThing = 1;"]),
    "TS-D2": (["const cfg = { a: 1 } satisfies Config;"],
              ["const a = 1;", "// satisfies the constraint"]),
    "TS-D3": (["const a = [1, 2] as const;"],
              ["const a = x as Const;", "const b = y as string;"]),
    "TS-D4": (["readonly name: string;", "let a: Readonly<Foo>;",
               "readonly [x, y]"],
              ["let readonlyish = 1;", "const a = 1;"]),
    "TS-D6": (["const a = obj?.prop;", "foo?.()"],
              ["const a = cond ? x : y;", "const b = obj.prop;"]),
    "TS-D7": (["const a = x ?? y;"],
              ["const a = x ? y : z;", "const b = x ??= y;",
               "const c = x || y;"]),
    # ---------------- TypeScript expressiveness ----------------
    "TS-C1": (["interface Box<T> { v: T }", "class A<T> {}",
               "function f<T>(x: T) {}"],
              ["const a = 1 < 2 > 0;", "let x: number;"]),
    "TS-C2": (["type T<A> = A extends string ? 1 : 2;"],
              ["class A extends B {}", "let x = a ? b : c;"]),
    "TS-C3": (["type E<T> = T extends Array<infer U> ? U : never;"],
              ["const inferred = 1;", "// infer the type"]),
    "TS-C4": (["type M<T> = { [K in keyof T]: string };",
               "{ [P in Keys]?: number }"],
              ["const a = obj[key];", "for (const k in obj) {}"]),
    "TS-C5": (["type R<T> = { [K in keyof T as `get${K}`]: 1 };"],
              ["type M<T> = { [K in keyof T]: 1 };"]),
    "TS-C6": (["type S = `prefix${Name}`;"], ["const s = 'plain';"]),
    "TS-C7": (["type K = keyof Foo;"], ["const keyofthing = 1;"]),
    "TS-C8": (["let a: typeof window;", "Array<typeof x>"],
              ["if (typeof x === 'string') {}"]),
    "TS-C9": (["type V = Foo[keyof Foo];"], ["const v = arr[0];"]),
    "TS-C10": (["type P = Partial<Foo>;", "let r: Record<string, number>;"],
               ["const partial = 1;", "class Pick {}"]),
    "TS-C11": (["type U = A | B;", "let x: string | number;"],
               # `e | 0` (bitwise or) is a known false positive no regex can
               # exclude without type information; TS-C11 is reliable=False.
               ["const a = b || c;"]),
    "TS-C12": (["type I = A & B;"], ["const a = b && c;"]),
    "TS-C13": (["kind: 'circle',", 'type: "square"'],
               ["kind: someVar,", "name: 'bob'"]),
    "TS-C14": (["name?: string;", "opts ?: Foo"],
               ["const a = b ? c : d;", "name: string;"]),
    "TS-C15": (["enum Color { Red }", "const enum Dir { Up }"],
               ["const enumerate = 1;", "class Enumerator {}"]),

    # ---------------- C# escape hatches ----------------
    "CS-E1": (["dynamic d = Get();", "var x = (dynamic)o;",
               "List<dynamic> l;", "dynamic[] arr;", "var y = o as dynamic;"],
              ["var dynamicValue = 1;", "[Dynamic] public int X;",
               'var s = "dynamic";', "class DynamicThing {}"]),
    "CS-E2": (["var n = obj!.Name;", "return value!;", "T x = default!;",
               "string s = null!;"],
              ["if (!flag) return;", "if (a != b) return;",
               "if (!(x is Foo)) return;", "var b = !IsValid(x);"]),
    "CS-E3": (["#nullable disable", "#nullable restore",
               "<Nullable>disable</Nullable>"],
              ["#nullable enable", "// nullable disable"]),
    "CS-E4": (["#pragma warning disable CS8618",
               "[SuppressMessage(\"x\", \"y\")]"],
              ["#pragma warning restore CS8618", "// suppress this"]),
    "CS-E5": (["unsafe { *p = 1; }", "public unsafe void F()",
               "fixed (byte* p = arr)", "var s = stackalloc byte[16];"],
              ["var safeValue = 1;", "class UnsafeHelper {}"]),
    "CS-E6": (["Unsafe.As<Foo>(ref x)", "MemoryMarshal.Cast<byte, int>(s)"],
              ["var x = As(y);", "Marshal.Copy(a, b, c, d);"]),
    "CS-E7": (["var a = (MyType)other;", "return (Foo)bar;"],
              ["var a = (1 + 2) * 3;", "if (x) { }"]),
    "CS-E8": (["var a = obj as MyType;", "return x as Foo[];"],
              ["using Alias = System.Int32;", "var b = obj as dynamic;"]),
    "CS-E9": (["object o = GetThing();", "List<object> items;",
               "private object _state;"],
              ["var o = new object();", "class ObjectPool {}"]),
    "CS-E10": (["t.GetMethod(\"X\").Invoke(o, null)",
                "Activator.CreateInstance(t)", "Type.GetType(name)"],
               ["obj.Method();", "var t = typeof(Foo);"]),
    # ---------------- C# safety ----------------
    "CS-D1": (["#nullable enable", "<Nullable>enable</Nullable>"],
              ["#nullable disable"]),
    "CS-D2": (["string? name;", "MyType? value,", "object? o)"],
              ["var a = b ? c : d;", "string name;"]),
    "CS-D3": (["if (o is Foo f)", "if (x is not null)", "if (o is Bar)"],
              ["var a = b;", "if (isReady)"]),
    "CS-D4": (["public record Person(string Name);", "public int X { get; init; }",
               "required string Name"],
              ["public class Person {}", "var record = 1;"]),
    "CS-D5": (["where T : class", "where TKey : notnull"],
              ["var where = 1;", "query.Where(x => x)"]),
    # ---------------- C# expressiveness ----------------
    "CS-C1": (["class Box<T> {}", "interface IRepo<TKey, TValue> {}"],
              ["var a = x < y;", 'var s = "<div>text</div>";',
               "List<int> items;"]),
    "CS-C2": (["interface IOut<out T> {}", "delegate void D<in T>();"],
              ["List<T> items;"]),
    "CS-C3": (["(int count, string name) t = x;"],
              ["Method(a, b);", "(x + y)"]),
    "CS-C4": (["using Alias = System.Collections.Generic.List<int>;"],
              ["using System;", "using (var s = new X()) {}"]),
    "CS-C5": (["readonly struct Point {}", "ref struct Span2 {}",
               "ref readonly int Get()"],
              ["struct Point {}", "readonly int x;"]),

    # ---------------- Rust escape hatches ----------------
    "RS-E1": (["unsafe { *p }", "let x = unsafe {"],
              ["// unsafe block follows", "// SAFETY: this is fine",
               "fn safe_thing() {}", 'let s = "unsafe {";']),
    "RS-E1b": (["unsafe fn raw(p: *mut u8) {}",
                'unsafe extern "C" fn cb() {}'],
               ["fn safe() {}", "// unsafe fn"]),
    "RS-E1c": (["unsafe impl Send for Foo {}", "unsafe impl Trait for Bar {}"],
               ["impl Foo for Bar {}"]),
    "RS-E1d": (["unsafe impl Send for Foo {}", "unsafe impl<T> Sync for B<T> {}"],
               ["unsafe impl Trait for Bar {}", "impl Send for Foo {}"]),
    "RS-E1e": (["unsafe trait Raw {}"], ["trait Safe {}"]),
    "RS-E1f": (["unsafe { }", "unsafe fn f()", "unsafe impl Send for A {}"],
               ["// SAFETY: justified", "fn safe() {}",
                'let s = "unsafe";']),
    "RS-E2": (["mem::transmute(x)", "transmute::<A, B>(v)",
               "slice::from_raw_parts(p, n)"],
              ["fn transmuter() {}", "// transmute is bad"]),
    "RS-E3": (["#[allow(dead_code)]", "#![allow(clippy::unwrap_used)]"],
              ["#[deny(warnings)]", "#[expect(dead_code)]"]),
    "RS-E4": (["v.get_unchecked(0)", "o.unwrap_unchecked()",
               "str::from_utf8_unchecked(b)"],
              ["v.get(0)", "o.unwrap()"]),
    "RS-E5": (["let v = o.unwrap();", "let v = r.expect(\"msg\");",
               "r.unwrap_err()"],
              ["o.unwrap_or(0)", "o.unwrap_or_else(|| 0)",
               "o.unwrap_or_default()", "// call unwrap here"]),
    "RS-E6": (["panic!(\"boom\");", "todo!()", "unreachable!()",
               "unimplemented!()"],
              ["fn panics() {}", "// todo: fix", "let panic_count = 0;"]),
    "RS-E7": (["let x = v[i];", "map[key]"],
              ["let a = 1;", "fn f() {}"]),
    "RS-E8": (["let n = x as u32;", "let p = q as *const u8;",
               "y as usize", "f as f64"],
              ["use foo as bar;", "s.as_ref()", "s.as_str()",
               "x as MyStruct"]),
    "RS-E9": (["RefCell<Vec<u8>>", "let v = cell.borrow_mut();",
               "Cell<u32>"],
              ["Mutex<Vec<u8>>", "RwLock<T>"]),
    "RS-E10": (["Box<dyn Any>", "v.downcast_ref::<Foo>()"],
               ["Box<dyn Error>", "dyn Trait"]),
    # ---------------- Rust safety ----------------
    "RS-D1": (["let v = f()?;", "g()?.h()", "let x = a?,"],
              ["fn f<T: ?Sized>(x: &T) {}", "let a = 1;"]),
    "RS-D2": (["u32::try_from(x)", "x.try_into()?", "impl TryFrom<u8> for A {}",
               "a.checked_add(b)"],
              ["u32::from(x)", "x.into()"]),
    "RS-D3": (["o.unwrap_or(0)", "o.unwrap_or_default()", "if let Some(v) = o",
               "r.map_err(|e| e)"],
              ["o.unwrap()", "let x = 1;"]),
    "RS-D4": (["#[expect(dead_code)]", "#![forbid(unsafe_code)]",
               "#![deny(unsafe_code)]"],
              ["#[allow(dead_code)]"]),
    "RS-D5": (["// SAFETY: pointer is valid", "/// SAFETY: checked above"],
              ["// this is safe", "unsafe { }"]),
    # ---------------- Rust expressiveness ----------------
    "RS-C1": (["fn f<T>(x: T) {}", "struct Wrapper<T> {}", "impl<T> Foo<T> {}"],
              ["fn g(x: u8) {}", "let a = b < c;"]),
    "RS-C2": (["fn f<'a>(s: &'a str) {}", "struct S<'a> { v: &'a u8 }"],
              ["let c = 'a';", "let n = '\\n';", "match c { 'x' => 1 }"]),
    "RS-C3": (["fn f<T: Clone>(x: T) {}", "struct S<T: Send + Sync> {}"],
              ["fn g<T>(x: T) {}"]),
    "RS-C4": (["where T: Clone,", "where 'a: 'b,"],
              ["let where_clause = 1;"]),
    "RS-C5": (["fn f() -> impl Iterator<Item = u8> {}",
               "fn g(x: impl Display) {}"],
              ["impl Display for Foo {}", "unsafe impl Send for A {}",
               "impl Foo {}"]),
    "RS-C6": (["Box<dyn Error>", "&dyn Display"],
              ["let dynamic = 1;"]),
    "RS-C7": (["type Result2 = Result<T, E>;", "type Map<K> = HashMap<K, u8>;"],
              ["let type_name = 1;"]),
    "RS-C8": (["type Item;", "Self::Output"],
              ["let x = 1;"]),
    "RS-C9": (["PhantomData<T>", "_marker: PhantomData<*const T>,"],
              ["let phantom = 1;"]),
    "RS-C10": (["enum Shape { Circle }"], ["let enumerate = 1;"]),
    "RS-C11": (["trait Draw {}"], ["let trait_name = 1;"]),
    "RS-C12": (["T: Send + Sync", "unsafe impl Send for A {}"],
               ["let sender = 1;"]),
    "RS-C13": (["Option<u8>", "Result<T, E>"],
               ["let optional = 1;", "OptionParser"]),
}


def _language_of(construct_id: str) -> str:
    return K.get(construct_id).language


@pytest.mark.parametrize("construct_id", sorted(CASES))
def test_positives(construct_id: str) -> None:
    c = K.get(construct_id)
    positives, _ = CASES[construct_id]
    assert positives, f"{construct_id} has no positive cases"
    for line in positives:
        prepared = line if needs_raw_text(c) else strip_line(line, c.language)
        assert c.count_line(prepared) > 0, (
            f"{construct_id} ({c.display_name}) failed to match a positive:\n"
            f"  raw      {line!r}\n  prepared {prepared!r}\n"
            f"  pattern  {c.pattern}")


@pytest.mark.parametrize("construct_id", sorted(CASES))
def test_negatives(construct_id: str) -> None:
    c = K.get(construct_id)
    _, negatives = CASES[construct_id]
    assert negatives, f"{construct_id} has no negative cases"
    for line in negatives:
        prepared = line if needs_raw_text(c) else strip_line(line, c.language)
        assert c.count_line(prepared) == 0, (
            f"{construct_id} ({c.display_name}) matched a negative:\n"
            f"  raw      {line!r}\n  prepared {prepared!r}\n"
            f"  pattern  {c.pattern}")


def test_catalogue_is_well_formed() -> None:
    K.validate_catalogue()


def test_every_construct_has_cases() -> None:
    missing = sorted(c.id for c in K.ALL if c.id not in CASES)
    assert not missing, f"constructs with no test cases: {missing}"
