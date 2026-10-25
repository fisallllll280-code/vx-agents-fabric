# VX Master Index and Tool Catalog v1

**Index ID:** `VX.INDEX.MASTER_CATALOG.V1`  
**State:** `PROPOSAL`  
**As of:** 2026-10-25  
**Scope:** available pinned repository snapshots connected to VX Agents Fabric  
**Mutation policy:** read-only; `project.genome` and `Ω.000` are protected

This is a source map for the accessible index families, not a claim that every historical record has been recovered. The source repos are pinned by commit so later refreshes can be compared without overwriting provenance.

## Repository and index map

| System | Index family | Snapshot | Current evidence and limit |
|---|---|---|---|
| VAIXLNS | Innovation operation index | `433969a43b604563e22b70b8cb88223aff539fad` | 177 generated records are present in the inspected index; 174 require review. The builder does not promote implementation or verification states. |
| VAIXLNS | Ω.000 master index | `433969a43b604563e22b70b8cb88223aff539fad` | Protected read-only source. The mounted snapshot was not copied; record count and completeness were not revalidated in this run. |
| VAIXLNS | Historical index families, roughly 0001–2750 | `433969a43b604563e22b70b8cb88223aff539fad` | VAIXLNS index README describes 40+ families and incomplete exposure of historical rows. Full historical recovery is not established. |
| NEXENT | Federated/master registry indexes and innovation boundary | `f62cf5920174551f9a8f88deb420f9515bedc284` | Source documents include the master federated index, canonical innovation index, complete inventory and boundary. Treat as source documents; no blanket implementation inference. |
| NEXENT | NXL language registry | `f62cf5920174551f9a8f88deb420f9515bedc284` | Nine language names are present; all are PROPOSED, with grammar and semantics still placeholders. Translation/compiler admission stays HOLD. |
| VX Agents Fabric | Ω-SYMBOL index | current PR branch | Emoji 18.0 import proposal; corpus hash is not pinned and source data are not mounted. |
| VX Agents Fabric | Master index/tool catalog | this change | A pointer index; it does not copy or rewrite canonical records. |

## VX engineering tools

The declared catalog contains six tools. Availability below means the implementation contract has a local handler; it does not imply a remote service is connected.

| Tool ID | Capability | Default state | Gate |
|---|---|---|---|
| `math.evaluate` | bounded arithmetic expression | local | expression allowlist and numeric bounds |
| `math.solve_linear_system` | bounded linear solver | local | square matrix, size cap, finite inputs |
| `engineering.convert_units` | dimensional unit conversion | local | supported units and dimension match |
| `github.fetch_file` | repository file read | configured adapter | read-only, repository/path validation |
| `sandbox.execute_python` | remote Python execution | not configured by default | configured user sandbox and bounded receipt |
| `engineering.solver.submit` | CAD/CAE/CFD solver job | not configured by default | allowlisted solver, external approval and job receipt |

## Evidence states

Use `RECOVERED` only for content actually present in a pinned source. Use `PROPOSED` for authored plans, `IMPLEMENTED` only for code present in a repository, and `VERIFIED` only for a claim with current, claim-bound evidence. CI success establishes only the checks actually run at that commit.

## Innovation packet path

`engineering.innovation_request` invokes the local `VX-ENG-INNOV` adapter and writes a deterministic packet into the workflow artifact archive. Packets are planning-only and include index pointers, tool routes, constraints, acceptance criteria, blockers and replay hashes. All execution stages remain `NOT_RUN` until their adapters and evidence are available.

Example context:

```json
{
  "engineering": {
    "innovation_request": {
      "goal": "Turn this challenge into a testable engineering concept",
      "domain": "software",
      "constraints": ["offline-first", "zero external spend"],
      "index_ids": ["VAIXLNS.INDEX.INNOVATION_OPERATION.V1"],
      "source_refs": []
    }
  }
}
```

The packet does not claim novelty, feasibility, implementation, validation or canonical admission. No external spend or canonical mutation is permitted by this local path.

## Repository integrity source audit

See [Claude Repository Integrity Changes — Source Audit v1](../research/CLAUDE_REPOSITORY_INTEGRITY_AUDIT_V1.md) for commit-level diff and test review. Existing VAIXLNS zero-loss indexing already captures content hashes, source revisions and symlink-target text. The candidate gap is nested repository boundary detection; the audit records the proposed work as PROPOSED and does not represent it as adopted or verified.
