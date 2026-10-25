# Claude Repository Integrity Changes — Source Audit v1

**Audit ID:** `VX-REPO-AUDIT-CLAUDE-20261025`  
**State:** `REVIEWED_SOURCE_DIFFS; NOT_TEST_EXECUTED_HERE`  
**Purpose:** compare upstream code and test changes with the existing VAIXLNS index-recovery implementation before adopting anything.

## Audited upstream commits

| Commit | Actual change | Test evidence in the commit | Relevance |
|---|---|---|---|
| [218862e](https://github.com/anthropics/claude-plugins-official/commit/218862e1b0814b66361e9d215c409a10df2304ae) | Resolves both the tool path and session directory with `realpath` if their absolute spellings differ, then retries the Git baseline lookup. The existing first lookup remains intact. | Adds symlink-parent and symlink-session-directory cases, including outside-repository and rewrite behavior. These are test additions, not proof that this audit ran them. | Useful when VX compares a file with a historical version through two path aliases. VAIXLNS's current indexer stores root-relative paths and symlink-target text; it does not perform this baseline lookup. |
| [a00d13d](https://github.com/anthropics/claude-plugins-official/commit/a00d13d77ba7bf13a9d2ae0db5f7e24aeb4b12b2) | Removes checked-out nested-repository gitlinks from a temporary index copy before Git commands can enter them. It uses bounded listing, literal pathspecs and falls back if isolation fails. The real Git index is left untouched. | Adds cases for unchanged real index, staged/committed nested repos, failed gitlink removal, absent checkout, unsupported sparse listing, timeout, glob-shaped names and repositories without gitlinks. | Directly relevant to the VAIXLNS source walk: its walker does not follow directory symlinks, but currently descends into non-excluded directories containing a nested `.git` file. This can mix nested repository files into the parent inventory. |
| [34d31be](https://github.com/anthropics/claude-plugins-official/commit/34d31be12a184ffe44e97e6c52ad4442bdaa7007) | On Windows, if OpenSSL cannot build the default TLS context due to unreadable certificate-store entries, builds a context from readable server-trusted certificates. Chain and hostname verification remain enabled; skipped certificates are counted. | Adds simulated Windows-store and HTTPS-handshake cases for unreadable stores, unreadable certificates, trusted/untrusted chains, hostname mismatch, store-list failure, request count and emitted metrics. | A general remote-provider resilience pattern. It is not needed by the current local-only VAIXLNS index builder and should not be copied into it. |
| [1e25068](https://github.com/anthropics/claude-plugins-official/commit/1e25068c2793a1c50c91c2941055ce5043c4a7fe) | Changes Security Guidance version metadata from 2.0.15 to 2.0.16. | No functional test change in this commit. | Release bookkeeping only. |

## Existing VAIXLNS implementation inspected

Snapshot: [VAIXLNS commit `433969a`](https://github.com/fisallllll280-code/VAIXLNS/tree/433969a43b604563e22b70b8cb88223aff539fad)

- `scripts/build_zero_loss_index.py` creates five artifacts and 28 views. It captures source SHA-256 values, source revision, source kind and record lineage.
- `_discover_sources` calls `os.walk(..., followlinks=False)`; directory links are recorded as link entries, and `_read_source` hashes link-target text. It does not recursively follow those links.
- `EXCLUDED_DIRS` excludes `.git` path components. A nested repository root whose own `.git` is a *file* is not recognized as a boundary by the parent walk; the walker can still traverse its ordinary source files.
- `scripts/recover_zero_loss_index.py` already runs the existing index test, builds, verifies, checks expected artifacts and hashes, and writes a separate receipt. It protects `project.genome` and `Ω.000` by policy.
- `tests/test_zero_loss_index.py` has eight named test methods in this snapshot. They cover deterministic output, source hashes/lineage, unresolved historical IDs, cross-reference semantics and promotion guards. They do not cover symlink alias baselines or nested Git repositories.
- The recovery protocol defines staged evidence and admission gates, but the snapshot does not prove the workflow was executed in this audit.

## Decision and proposed work register

| ID | Candidate work | State | Recommended placement |
|---|---|---|---|
| `VX-REPO-001` | Detect nested repository boundaries during the existing source walk; preserve parent-path and gitlink revision evidence, and do not silently mix nested contents into the parent index. | `PROPOSED` | Extend the existing VAIXLNS builder only after deciding whether nested repositories are separate pinned sources or excluded boundaries with receipts. |
| `VX-REPO-002` | Content identity and historical comparison across path aliases. | `PARTLY_PRESENT` | Reuse existing SHA-256/source-revision records. Add alias-baseline lookup only to a workflow that actually compares historical file contents. |
| `VX-REPO-003` | Fault-injection coverage for symlinks, nested repositories, unreadable paths, and unavailable Git capabilities. | `PROPOSED` | Add focused cases to the current builder tests; test all fallback paths and prove the source checkout remains unchanged. |
| `VX-REPO-004` | Evidence gate for result states and promotion. | `PRESENT_WITH_SCOPE_LIMITS` | Reuse the existing recovery receipt and verify-only pass. Keep `PASS`, `FAIL`, `UNKNOWN`, and `ERROR` distinct for each step; an overall run must not hide a failed or unattempted stage. |

## Adoption gates

1. Pin the VAIXLNS base commit and record hashes of `project.genome` and `Ω.000` before and after work.
2. Define the nested-source policy: separate pinned source, submodule gitlink record, or unresolved/excluded boundary. Never infer ownership from directory name.
3. Add tests proving symlink directories are not traversed and nested repository contents cannot leak into parent records.
4. Prove test fixtures did not mutate the real Git index or source repository; test fail-closed behavior when boundary detection fails.
5. Run the prescribed VAIXLNS test and recovery workflow in an isolated branch; retain output, exit codes and artifact hashes.
6. Keep promotion `HOLD` until independent review confirms every claimed behavior from the generated receipts.

No VAIXLNS code was changed by this audit, and none of the upstream changes are represented as adopted or verified.
