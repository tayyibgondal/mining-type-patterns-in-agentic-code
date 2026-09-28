All top-100 TypeScript repos were scanned, `human_ts_prs.csv` now has **12,690 PRs.**

The CSV file size is 179MB. Therefore, please open it with pandas rather than Excel or numbers (MacOS).

| State    | PRs   |
| -------- | ----- |
| Merged   | 9,952 |
| Rejected | 2,596 |
| Pending  | 142   |

- No crashes, network errors or timeouts, and no PR appears twice.
- Only 70 of the 100 repos contributed rows. The other 30 had nothing that passed the filters. That's mostly repos like developer-roadmap that weren't TypeScript before mid-2021 (52,846 PRs were dropped for touching no .ts files) or were dominated by bots (15,598 dropped).
- 2,704 PRs were removed for dependency changes: 1,932 lock files, 680 package.json edits and 92 by title.
- File size: the CSV is 179MB. Open it with pandas rather than Excel, since Excel truncates cells over 32,767 characters and many diffs are longer than that.
