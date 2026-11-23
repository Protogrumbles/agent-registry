# agent-registry

A tiny agent governance registry: register every AI agent / automation in
one place, with an owner, a scope, its data access, its model/tool, and a
status — plus a kill-switch (revoke) and an append-only audit log of every
change.

Built by Sean Steuer — Program Manager, AI Strategy & Operational
Transformation at Netflix. This generalizes a **governance pattern** from
that work: know what agents exist, who owns them, what data they can touch,
and how to turn one off. It is a pattern, not real Netflix data, code, or
internal tooling. All sample agents in this repo are fictional (Northlight
Studios, Harbor Lane Studio) and labeled as such.

## What it is

- A stdlib-only Python CLI + JSON/CSV store (`registry.py`, no dependencies).
- `register` an agent: name, owner, scope, data access, model/tool, status.
- `list` / `search` agents by owner, status, or free text.
- `revoke` (kill-switch) an agent with a reason and a timestamp — and
  `status` to change an agent's state with the same paper trail.
- An **append-only audit log** (`audit.jsonl`): one JSON object per line for
  every register / revoke / status change. Never edited in place.
- A one-page registry report (Markdown) for review meetings.

## What it is NOT

- Not an enforcement system. Revoking an agent here records the decision
  and the reason; it does not itself shut down a vendor account, a cron job,
  or a deployed service. A human (or your provisioning automation) acts on it.
- Not access control. It records *declared* data access; it does not verify
  it against real permissions.
- Not a secret store. Never put API keys or credentials in a registry entry.

## Quick start

```bash
# Register a (fictional) agent
python3 registry.py register --store ./registry-data \
  --name summary-bot --owner sean --scope "Summarize meeting notes" \
  --data-access "meeting transcripts (read-only)" \
  --model "vendor-model-x" --tool "summary-bot v0.1"

# List everything, then search
python3 registry.py list --store ./registry-data
python3 registry.py search --store ./registry-data --query summary

# Kill-switch it, with a reason
python3 registry.py revoke --store ./registry-data --name summary-bot \
  --reason "Cost spike under review"

# See the audit trail, then build the report
python3 registry.py audit --store ./registry-data
python3 registry.py report --store ./registry-data --out report.md
```

Python 3.9+; no dependencies.

## Data model

`registry-data/registry.json` — one object per agent:

```json
{
  "summary-bot": {
    "name": "summary-bot", "owner": "sean",
    "scope": "Summarize meeting notes",
    "data_access": "meeting transcripts (read-only)",
    "model": "vendor-model-x", "tool": "summary-bot v0.1",
    "status": "active",
    "created_at": "2026-11-23T09:00:00",
    "updated_at": "2026-11-23T09:00:00"
  }
}
```

Statuses: `active`, `paused`, `revoked`. Revoking sets `status` to
`revoked` and records `revoked_at` and `revoke_reason` on the entry.

`registry-data/audit.jsonl` — append-only, one event per line:

```json
{"ts": "2026-11-23T09:00:00", "event": "register", "name": "summary-bot", "actor": "sean", "detail": "..."}
```

Events: `register`, `revoke`, `status_change`. The CLI never rewrites
`audit.jsonl`; it only appends.

## Tests

```bash
python3 -m unittest discover -s tests -v
```

Tests cover the full lifecycle — register → list → revoke → audit log
shows all events → report generated — plus the negative paths (revoking
or changing the status of an unknown agent fails cleanly).

## Layout

```
registry.py        CLI + store logic (stdlib only)
examples/registry.json   Example registry (fictional agents)
examples/audit.jsonl     Example audit log (fictional)
tests/test_registry.py
```
