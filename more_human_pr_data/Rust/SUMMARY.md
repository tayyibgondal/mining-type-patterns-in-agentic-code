All top-100 Rust repos were scanned, `human_rust_prs.csv` now has **15,417 PRs.**

The CSV file size is 244MB. Therefore, please open it with pandas rather than Excel or numbers (MacOS).

| State    | PRs    |
| -------- | ------ |
| Merged   | 12,747 |
| Rejected | 2,629  |
| Pending  | 41     |

- No crashes, network errors or timeouts, and no PR appears twice. 16 PRs were skipped because GitHub returned a server error (HTTP 500) for their diff.
- 84 of the 100 repos contributed rows, and large repos like rust-lang/rust, tauri, deno, ripgrep and alacritty each reached the 300-PR limit. The other 16 had nothing that passed the filters: 11 weren't Rust before mid-2021 (e.g. fish-shell, influxdb, ccxt), 3 (lapce, bun, redox) had no PRs before the cutoff, and 2 (difftastic, rust-course) had only a handful, mostly from bots. Overall, 27,151 PRs were dropped for touching no .rs files and 6,207 for bot or deleted-account authors.
- 3,984 PRs were removed for dependency changes: 2,440 Cargo.lock changes, 1,353 Cargo.toml edits and 191 by title.
- 48 "Rollup of N pull requests" PRs were excluded, since they bundle other people's already-submitted PRs (duplicate diffs, wrong author). None remain in the CSV.
- File size: the CSV is 244MB. Open it with pandas rather than Excel.
