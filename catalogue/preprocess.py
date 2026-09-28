"""Turn a unified diff into the lines the catalogue patterns run against.

Section 7.1 of `docs/type_patterns_and_escape_hatches.md`:

  1. added (`+`) and removed (`-`) lines are counted separately, never on the
     concatenated patch;
  2. comments and string literals are stripped before matching, so that
     `"type": "any"` in a JSON blob and `<div>` inside an HTML template no
     longer count as constructs;
  3. suppression directives and `// SAFETY:` comments are read from the raw
     line, because stripping comments would destroy exactly what they are;
  4. only hand-written source files of the target language are counted.

The old pipeline did none of this. The Rust `unsafe` counter matched the word
inside `// SAFETY:` prose, and the C# generics counter matched every HTML tag
that appeared inside a string.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field

# --------------------------------------------------------------------------
# File filtering
# --------------------------------------------------------------------------

SOURCE_SUFFIXES: dict[str, tuple[str, ...]] = {
    "TypeScript": (".ts", ".tsx", ".mts", ".cts"),
    "C#": (".cs",),
    "Rust": (".rs",),
}

# Config files are read only for the per-PR strictness flags (TS-E9, CS-E3).
CONFIG_NAMES: dict[str, tuple[str, ...]] = {
    "TypeScript": ("tsconfig.json",),
    "C#": (".csproj", "directory.build.props"),
    "Rust": (),
}

# Generated or vendored code is not hand-written and must not be counted.
EXCLUDED_PATTERNS: dict[str, tuple[str, ...]] = {
    "TypeScript": (
        r"\.d\.ts$",              # ambient declarations, tracked separately
        r"(^|/)node_modules/",
        r"(^|/)dist/", r"(^|/)build/", r"(^|/)out/",
        r"\.min\.[jt]s$",
        r"(^|/)__generated__/", r"\.generated\.ts$", r"\.gen\.ts$",
    ),
    "C#": (
        r"\.designer\.cs$", r"\.g\.cs$", r"\.g\.i\.cs$",
        r"\.generated\.cs$", r"\.feature\.cs$",
        r"(^|/)obj/", r"(^|/)bin/",
        r"assemblyinfo\.cs$",
    ),
    "Rust": (
        r"(^|/)target/",
        r"\.pb\.rs$", r"(^|/)build\.rs$",
        r"(^|/)bindings?\.rs$",
    ),
}

# RS-E6 (panic macros) is expected and idiomatic in tests and benchmarks.
TEST_PATH_PATTERNS = (
    r"(^|/)tests?/", r"(^|/)benches/", r"(^|/)__tests__/",
    r"\.test\.[jt]sx?$", r"\.spec\.[jt]sx?$", r"tests?\.rs$",
)

_EXCLUDED_RX = {
    lang: [re.compile(p, re.IGNORECASE) for p in pats]
    for lang, pats in EXCLUDED_PATTERNS.items()
}
_TEST_RX = [re.compile(p, re.IGNORECASE) for p in TEST_PATH_PATTERNS]


def is_source_file(path: str, language: str) -> bool:
    """A hand-written source file of the target language."""
    if not path:
        return False
    low = path.lower()
    if not low.endswith(SOURCE_SUFFIXES[language]):
        return False
    return not any(rx.search(low) for rx in _EXCLUDED_RX[language])


def is_config_file(path: str, language: str) -> bool:
    low = (path or "").lower()
    names = CONFIG_NAMES[language]
    return bool(names) and any(low.endswith(n) or low == n for n in names)


def is_test_path(path: str) -> bool:
    low = (path or "").lower()
    return any(rx.search(low) for rx in _TEST_RX)


# --------------------------------------------------------------------------
# Comment and string stripping
# --------------------------------------------------------------------------

_RUST_CHAR = re.compile(r"'(?:\\.|[^\\'])'")


def strip_line(line: str, language: str) -> str:
    """Blank out comment and string-literal content, preserving structure.

    Replaces the *contents* of literals rather than deleting them, so that
    column-sensitive patterns still see a token where a string used to be.
    A Rust lifetime (`'a`) is not a char literal and is preserved; a char
    literal (`'a'`) is not a lifetime and is blanked.
    """
    out: list[str] = []
    i, n = 0, len(line)
    while i < n:
        ch = line[i]

        # ---- line comment ------------------------------------------------
        if ch == "/" and i + 1 < n and line[i + 1] == "/":
            break

        # ---- block comment ----------------------------------------------
        if ch == "/" and i + 1 < n and line[i + 1] == "*":
            end = line.find("*/", i + 2)
            if end == -1:
                break               # runs past end of line
            i = end + 2
            continue

        # ---- Rust raw string r"..." / r#"..."# ---------------------------
        if language == "Rust" and ch == "r" and i + 1 < n:
            m = re.match(r'r(#*)"', line[i:])
            if m and (i == 0 or not (line[i - 1].isalnum() or line[i - 1] == "_")):
                hashes = m.group(1)
                close = '"' + hashes
                end = line.find(close, i + len(m.group(0)))
                out.append('""')
                i = (end + len(close)) if end != -1 else n
                continue

        # ---- C# verbatim / interpolated string ---------------------------
        if language == "C#" and ch in "@$" and i + 1 < n:
            m = re.match(r'[@$]{1,2}"', line[i:])
            if m:
                j = i + len(m.group(0))
                while j < n:
                    if line[j] == '"':
                        if j + 1 < n and line[j + 1] == '"':
                            j += 2
                            continue
                        break
                    j += 1
                out.append('""')
                i = j + 1 if j < n else n
                continue

        # ---- Rust char literal vs lifetime -------------------------------
        if language == "Rust" and ch == "'":
            m = _RUST_CHAR.match(line, i)
            if m:
                out.append("''")
                i = m.end()
                continue
            out.append(ch)          # a lifetime, keep it
            i += 1
            continue

        # ---- ordinary string literal -------------------------------------
        if ch in "\"'`" or (language == "TypeScript" and ch == "`"):
            quote = ch
            j = i + 1
            while j < n:
                if line[j] == "\\":
                    j += 2
                    continue
                if line[j] == quote:
                    break
                j += 1
            out.append(quote * 2)
            i = j + 1 if j < n else n
            continue

        out.append(ch)
        i += 1

    return "".join(out)


# --------------------------------------------------------------------------
# Diff parsing
# --------------------------------------------------------------------------

_DIFF_GIT = re.compile(r"^diff --git a/(?P<a>.+?) b/(?P<b>.+)$")
_PLUS_FILE = re.compile(r"^\+\+\+ (?:b/)?(?P<path>.+?)(?:\t.*)?$")
_MINUS_FILE = re.compile(r"^--- (?:a/)?(?P<path>.+?)(?:\t.*)?$")

# The AIDev arm does not carry standard unified-diff file headers. The
# extractors concatenated per-file patches under a custom banner:
#     === src/cli/init.ts (+1.0/-1.0) ===
# Supporting only `diff --git` here silently produced zero counts for every
# agent PR, which is exactly the failure this parser exists to prevent.
_AIDEV_FILE = re.compile(
    r"^=== (?P<path>.+?) \(\+[\d.]+/-[\d.]+\) ===\s*$")


@dataclass
class DiffLine:
    raw: str        # the line body, `+`/`-` marker removed, comments intact
    clean: str      # comments and string contents blanked out
    path: str
    is_test: bool


@dataclass
class PreparedDiff:
    """Everything the counters need from one PR's patch."""

    added: list[DiffLine] = field(default_factory=list)
    removed: list[DiffLine] = field(default_factory=list)
    source_files: set[str] = field(default_factory=set)
    config_lines: list[str] = field(default_factory=list)
    skipped_files: set[str] = field(default_factory=set)

    @property
    def files_counted(self) -> int:
        return len(self.source_files)

    @property
    def lines_added(self) -> int:
        return len(self.added)

    @property
    def lines_removed(self) -> int:
        return len(self.removed)


def prepare(patch_text: str | None, language: str) -> PreparedDiff:
    """Parse a unified diff into filtered, preprocessed added/removed lines.

    Tracks the current file across hunks so the language and generated-code
    filters apply per file, not per PR. Lines belonging to files that fail the
    filter are dropped entirely rather than counted against the PR.
    """
    prepared = PreparedDiff()
    if not patch_text or not isinstance(patch_text, str):
        return prepared

    current = ""
    counting = False
    in_config = False

    def switch_to(path: str) -> None:
        nonlocal current, counting, in_config
        current = path
        counting = is_source_file(path, language)
        in_config = is_config_file(path, language)
        if counting:
            prepared.source_files.add(path)
        elif path:
            prepared.skipped_files.add(path)

    for line in patch_text.splitlines():
        # ---- file headers ------------------------------------------------
        m = _AIDEV_FILE.match(line)
        if m:
            switch_to(m.group("path"))
            continue

        m = _DIFF_GIT.match(line)
        if m:
            current = m.group("b")
            counting = is_source_file(current, language)
            in_config = is_config_file(current, language)
            if counting:
                prepared.source_files.add(current)
            elif current:
                prepared.skipped_files.add(current)
            continue

        if line.startswith("+++"):
            m = _PLUS_FILE.match(line)
            if m:
                path = m.group("path")
                if path != "/dev/null":
                    current = path
                    counting = is_source_file(current, language)
                    in_config = is_config_file(current, language)
                    if counting:
                        prepared.source_files.add(current)
                    elif current:
                        prepared.skipped_files.add(current)
            continue

        if line.startswith("---") or line.startswith("@@") or \
                line.startswith("index ") or line.startswith("diff "):
            continue

        if not line:
            continue

        marker, body = line[0], line[1:]
        if marker not in "+-":
            continue

        if in_config and marker == "+":
            prepared.config_lines.append(body)
            continue

        if not counting:
            continue

        entry = DiffLine(raw=body,
                         clean=strip_line(body, language),
                         path=current,
                         is_test=is_test_path(current))
        (prepared.added if marker == "+" else prepared.removed).append(entry)

    return prepared


def prepare_files(files: list[tuple[str, str | None]],
                  language: str) -> PreparedDiff:
    """Prepare from explicit (filename, patch) pairs.

    The AIDev tables store one row per changed file, so the extractor can pass
    filenames directly instead of round-tripping through a concatenated blob
    and re-parsing a banner. Preferred over `prepare` wherever the file names
    are already known.
    """
    prepared = PreparedDiff()
    for path, patch in files:
        if is_config_file(path, language) and patch:
            prepared.config_lines.extend(
                line[1:] for line in patch.splitlines() if line.startswith("+"))
            continue
        if not is_source_file(path, language):
            if path:
                prepared.skipped_files.add(path)
            continue
        prepared.source_files.add(path)
        if not patch:
            continue
        test = is_test_path(path)
        for line in patch.splitlines():
            if not line or line[0] not in "+-":
                continue
            if line.startswith(("+++", "---")):
                continue
            body = line[1:]
            entry = DiffLine(raw=body,
                             clean=strip_line(body, language),
                             path=path, is_test=test)
            (prepared.added if line[0] == "+" else prepared.removed).append(entry)
    return prepared
