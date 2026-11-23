#!/usr/bin/env python3
"""agent-registry: tiny agent governance registry. Stdlib only.

Register agents (name, owner, scope, data access, model/tool, status),
list/search them, revoke (kill-switch) with reason + timestamp, keep an
append-only audit log (JSONL), and build a one-page Markdown report.

All sample data is fictional. Revoking records a decision; it does not
itself shut down any external system.
"""
import argparse, json, sys
from datetime import datetime
from pathlib import Path

VERSION = "0.1.0"
STATUSES = ("active", "paused", "revoked")

def now_iso():
    return datetime.now().isoformat(timespec="seconds")

def store_paths(store):
    d = Path(store); d.mkdir(parents=True, exist_ok=True)
    return d / "registry.json", d / "audit.jsonl"

def load_registry(store):
    reg_path, _ = store_paths(store)
    if not reg_path.exists():
        return {}
    data = json.loads(reg_path.read_text())
    if not isinstance(data, dict):
        raise ValueError("registry.json must be a JSON object keyed by agent name")
    return data

def save_registry(store, data):
    reg_path, _ = store_paths(store)
    reg_path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n")

def append_audit(store, event, name, actor, detail=""):
    _, audit_path = store_paths(store)
    entry = {"ts": now_iso(), "event": event, "name": name,
             "actor": actor, "detail": detail}
    with audit_path.open("a") as f:
        f.write(json.dumps(entry) + "\n")
    return entry

def load_audit(store):
    _, audit_path = store_paths(store)
    if not audit_path.exists():
        return []
    return [json.loads(line) for line in audit_path.read_text().splitlines() if line.strip()]

def cmd_register(args):
    data = load_registry(args.store)
    if args.name in data:
        print(f"error: agent {args.name!r} is already registered (use status to change it)", file=sys.stderr)
        return 2
    ts = now_iso()
    data[args.name] = {
        "name": args.name, "owner": args.owner, "scope": args.scope,
        "data_access": args.data_access, "model": args.model, "tool": args.tool,
        "status": args.status, "created_at": ts, "updated_at": ts,
    }
    save_registry(args.store, data)
    append_audit(args.store, "register", args.name, args.owner,
                 f"Registered {args.name} (scope: {args.scope}; data: {args.data_access}; model: {args.model}; tool: {args.tool}; status: {args.status}).")
    print(f"Registered {args.name} (status: {args.status})")
    return 0

def cmd_list(args):
    data = load_registry(args.store)
    rows = [v for v in data.values()
            if (not args.status or v["status"] == args.status)
            and (not args.owner or v["owner"] == args.owner)]
    rows.sort(key=lambda r: r["name"])
    if not rows:
        print("No agents registered." if not data else "No agents match the filter.")
        return 0
    print(f"{'NAME':<20} {'OWNER':<12} {'STATUS':<10} SCOPE")
    for r in rows:
        print(f"{r['name']:<20} {r['owner']:<12} {r['status']:<10} {r['scope']}")
    return 0

def cmd_search(args):
    data = load_registry(args.store)
    q = args.query.lower()
    hits = [v for v in data.values()
            if q in " ".join(str(x) for x in v.values()).lower()]
    hits.sort(key=lambda r: r["name"])
    if not hits:
        print(f"No agents match {args.query!r}.")
        return 0
    for r in hits:
        print(f"{r['name']} ({r['status']}, owner: {r['owner']}) — {r['scope']} — data: {r['data_access']} — {r['model']} / {r['tool']}")
    return 0

def _change_status(args, new_status, event, detail):
    data = load_registry(args.store)
    if args.name not in data:
        print(f"error: no agent named {args.name!r} is registered", file=sys.stderr)
        return 2
    entry = data[args.name]
    entry["status"] = new_status
    entry["updated_at"] = now_iso()
    if new_status == "revoked":
        entry["revoked_at"] = entry["updated_at"]
        entry["revoke_reason"] = args.reason or ""
    save_registry(args.store, data)
    append_audit(args.store, event, args.name, args.actor, detail)
    print(f"{args.name} -> {new_status}" + (f" ({args.reason})" if args.reason else ""))
    return 0

def cmd_revoke(args):
    if not args.reason:
        print("error: --reason is required when revoking an agent", file=sys.stderr)
        return 2
    return _change_status(args, "revoked", "revoke", f"Revoked: {args.reason}")

def cmd_status(args):
    return _change_status(args, args.new_status, "status_change",
                          f"Status changed to {args.new_status}" + (f": {args.reason}" if args.reason else "."))

def cmd_audit(args):
    events = load_audit(args.store)
    if not events:
        print("Audit log is empty.")
        return 0
    for e in events:
        print(f"{e['ts']}  {e['event']:<13} {e['name']}  ({e.get('actor','?')})  {e.get('detail','')}")
    return 0

def cmd_report(args):
    data = load_registry(args.store)
    events = load_audit(args.store)
    lines = ["# Agent Registry Report", "",
             f"Generated: {now_iso()}  ",
             f"Agents: **{len(data)}** — active: **{sum(1 for v in data.values() if v['status']=='active')}**, "
             f"paused: **{sum(1 for v in data.values() if v['status']=='paused')}**, "
             f"revoked: **{sum(1 for v in data.values() if v['status']=='revoked')}**  ",
             f"Audit events: **{len(events)}**",
             "",
             "> Fictional example data unless this store was built from your own "
             "agents. This report records declared scope and data access; it does "
             "not verify permissions.",
             "",
             "## Agents", "",
             "| Name | Owner | Status | Scope | Data access | Model / Tool |",
             "|---|---|---|---|---|---|"]
    for r in sorted(data.values(), key=lambda x: x["name"]):
        lines.append(f"| {r['name']} | {r['owner']} | {r['status']} | {r['scope']} | {r['data_access']} | {r['model']} / {r['tool']} |")
    lines += ["", "## Recent audit events", ""]
    for e in events[-10:]:
        lines.append(f"- {e['ts']} — **{e['event']}** {e['name']}: {e.get('detail','')}")
    if not events:
        lines.append("No audit events yet.")
    lines.append("")
    out = Path(args.out); out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("\n".join(lines))
    print(f"Wrote {out} ({len(data)} agents, {len(events)} audit events)")
    return 0

def main(argv=None):
    p = argparse.ArgumentParser(prog="registry.py", description="Tiny agent governance registry.")
    p.add_argument("--version", action="version", version=VERSION)
    sub = p.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("register", help="Register an agent")
    r.add_argument("--store", required=True); r.add_argument("--name", required=True)
    r.add_argument("--owner", required=True); r.add_argument("--scope", required=True)
    r.add_argument("--data-access", required=True); r.add_argument("--model", required=True)
    r.add_argument("--tool", required=True); r.add_argument("--status", default="active", choices=STATUSES)
    r.set_defaults(fn=cmd_register)
    l = sub.add_parser("list", help="List agents"); l.add_argument("--store", required=True)
    l.add_argument("--status", choices=STATUSES); l.add_argument("--owner"); l.set_defaults(fn=cmd_list)
    s = sub.add_parser("search", help="Search agents by free text")
    s.add_argument("--store", required=True); s.add_argument("--query", required=True); s.set_defaults(fn=cmd_search)
    v = sub.add_parser("revoke", help="Revoke (kill-switch) an agent")
    v.add_argument("--store", required=True); v.add_argument("--name", required=True)
    v.add_argument("--reason", required=True); v.add_argument("--actor", default="sean"); v.set_defaults(fn=cmd_revoke)
    t = sub.add_parser("status", help="Change an agent's status")
    t.add_argument("--store", required=True); t.add_argument("--name", required=True)
    t.add_argument("--new-status", required=True, choices=STATUSES)
    t.add_argument("--reason"); t.add_argument("--actor", default="sean"); t.set_defaults(fn=cmd_status)
    a = sub.add_parser("audit", help="Show the append-only audit log")
    a.add_argument("--store", required=True); a.set_defaults(fn=cmd_audit)
    rep = sub.add_parser("report", help="Build a one-page Markdown registry report")
    rep.add_argument("--store", required=True); rep.add_argument("--out", required=True); rep.set_defaults(fn=cmd_report)
    args = p.parse_args(argv)
    return args.fn(args)

if __name__ == "__main__":
    raise SystemExit(main())
