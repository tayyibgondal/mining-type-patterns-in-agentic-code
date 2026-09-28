All top-100 C# repos were scanned, `human_csharp_prs.csv` now has **15,260 PRs.**

The CSV file size is 421MB. Therefore, please open it with pandas rather than Excel or numbers (MacOS).

| State    | PRs    |
| -------- | ------ |
| Merged   | 12,199 |
| Rejected | 2,922  |
| Pending  | 139    |

- There were two network errors (the timeout after the Mac woke up, and a dropped connection at 20:39). The scraper retried both on its own. No PR appears twice.
- 90 of the 100 repos contributed rows, and large repos like jellyfin, PowerShell, dotnet/aspnetcore and Avalonia each reached the 300-PR limit.
- 12,972 PRs changed no .cs files, 3,074 were by bots or deleted accounts, and 1,645 were dependency changes (1,139 <PackageReference> edits, 403 NuGet files, 44 project.json edits, 59 by title).
- File size: the CSV is 421MB. Open it with pandas rather than Excel.
