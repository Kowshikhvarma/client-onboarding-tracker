"""Portfolio-level onboarding KPIs."""

from __future__ import annotations

from collections import Counter, defaultdict
from statistics import mean, median

from tracker.models import Client, Task


def portfolio_metrics(clients: list[Client]) -> dict:
    tasks: list[Task] = [t for c in clients for t in c.tasks]
    completed = [t for t in tasks if t.done]
    live = [c for c in clients if c.go_live_date]
    ttv = [c.days_to_go_live for c in live]
    live_on_target = [c for c in live if c.go_live_date <= c.target_go_live]

    workload: dict[str, dict] = defaultdict(lambda: {"clients": 0, "open_tasks": 0, "overdue": 0})
    for c in clients:
        if c.go_live_date:
            continue
        w = workload[c.csm_owner]
        w["clients"] += 1
        w["open_tasks"] += sum(not t.done for t in c.tasks)
        w["overdue"] += len(c.overdue_tasks)

    return {
        "clients_total": len(clients),
        "in_onboarding": sum(1 for c in clients if not c.go_live_date),
        "live": len(live),
        "health": dict(Counter(c.health for c in clients)),
        "overdue_tasks": sum(t.is_overdue for t in tasks),
        "task_on_time_pct": round(100 * sum(t.on_time for t in completed) / len(completed), 1) if completed else None,
        "avg_days_to_go_live": round(mean(ttv), 1) if ttv else None,
        "median_days_to_go_live": median(ttv) if ttv else None,
        "go_live_on_target_pct": round(100 * len(live_on_target) / len(live), 1) if live else None,
        "csm_workload": dict(sorted(workload.items())),
    }
