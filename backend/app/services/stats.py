"""Dashboard statistics - always computed from real database rows."""

from __future__ import annotations

import statistics
from datetime import date, datetime, timedelta

from sqlalchemy import desc, distinct, func, select
from sqlalchemy.orm import Session

from app.constants import CATEGORIES, RESOLVED, STATUSES, VERIFICATION_STATUSES
from app.db_types import utcnow
from app.models import Complaint, EvidenceFile
from app.services.complaints import IST

DATASETS = ("live", "demo", "all")


def dataset_conditions(dataset: str) -> list:
    if dataset == "live":
        return [Complaint.is_demo.is_(False)]
    if dataset == "demo":
        return [Complaint.is_demo.is_(True)]
    return []


def _month_start(d: date) -> date:
    return d.replace(day=1)


def _add_months(d: date, months: int) -> date:
    y, m = divmod(d.month - 1 + months, 12)
    return date(d.year + y, m + 1, 1)


def compute(db: Session, dataset: str = "all") -> dict:
    cond = dataset_conditions(dataset)

    by_status = dict(db.execute(
        select(Complaint.status, func.count()).where(*cond).group_by(Complaint.status)
    ).all())
    by_category = dict(db.execute(
        select(Complaint.category, func.count()).where(*cond).group_by(Complaint.category)
    ).all())
    by_verification = dict(db.execute(
        select(Complaint.verification_status, func.count()).where(*cond).group_by(Complaint.verification_status)
    ).all())
    total = sum(by_status.values())

    count_col = func.count().label("n")
    villages = db.execute(
        select(Complaint.village, Complaint.district, Complaint.state, count_col)
        .where(*cond).group_by(Complaint.village, Complaint.district, Complaint.state)
        .order_by(desc("n"), Complaint.village).limit(10)
    ).all()
    districts = db.execute(
        select(Complaint.district, Complaint.state, count_col)
        .where(*cond).group_by(Complaint.district, Complaint.state)
        .order_by(desc("n"), Complaint.district).limit(10)
    ).all()
    distinct_villages = db.scalar(
        select(func.count()).select_from(
            select(Complaint.village, Complaint.district).where(*cond).distinct().subquery()
        )
    ) or 0
    with_evidence = db.scalar(
        select(func.count(distinct(EvidenceFile.complaint_id))).join(Complaint).where(*cond)
    ) or 0
    unread_updates = db.scalar(
        select(func.count()).select_from(Complaint).where(*cond, Complaint.has_unread_update.is_(True))
    ) or 0
    info_requested = db.scalar(
        select(func.count()).select_from(Complaint).where(*cond, Complaint.info_requested.is_(True))
    ) or 0

    # --- Time series (Indian Standard Time) --------------------------------
    now_ist = utcnow().astimezone(IST)
    today = now_ist.date()
    first_month = _add_months(_month_start(today), -11)
    since = datetime.combine(first_month, datetime.min.time(), tzinfo=IST)
    stamps = db.scalars(select(Complaint.submitted_at).where(*cond, Complaint.submitted_at >= since)).all()

    daily_counts: dict[date, int] = {}
    monthly_counts: dict[date, int] = {}
    for stamp in stamps:
        d = stamp.astimezone(IST).date()
        daily_counts[d] = daily_counts.get(d, 0) + 1
        monthly_counts[_month_start(d)] = monthly_counts.get(_month_start(d), 0) + 1
    daily = [
        {"date": (today - timedelta(days=i)).isoformat(), "count": daily_counts.get(today - timedelta(days=i), 0)}
        for i in range(29, -1, -1)
    ]
    monthly = [
        {"month": _add_months(first_month, i).strftime("%Y-%m"), "count": monthly_counts.get(_add_months(first_month, i), 0)}
        for i in range(12)
    ]

    # --- Resolution time ---------------------------------------------------
    resolved_rows = db.execute(
        select(Complaint.submitted_at, Complaint.closed_at)
        .where(*cond, Complaint.status == RESOLVED, Complaint.closed_at.is_not(None))
    ).all()
    durations = [(closed - submitted).total_seconds() / 86400 for submitted, closed in resolved_rows]
    median_days = round(statistics.median(durations), 1) if durations else None

    return {
        "dataset": dataset,
        "total": total,
        "by_status": [{"status": s, "label": label, "count": by_status.get(s, 0)} for s, label in STATUSES.items()],
        "by_category": [{"category": c, "label": label, "count": by_category.get(c, 0)} for c, label in CATEGORIES.items()],
        "by_verification": [{"status": v, "label": label, "count": by_verification.get(v, 0)}
                            for v, label in VERIFICATION_STATUSES.items()],
        "top_villages": [{"village": v, "district": d, "state": s, "count": n} for v, d, s, n in villages],
        "top_districts": [{"district": d, "state": s, "count": n} for d, s, n in districts],
        "distinct_villages": distinct_villages,
        "with_evidence": with_evidence,
        "unread_updates": unread_updates,
        "info_requested": info_requested,
        "daily": daily,
        "monthly": monthly,
        "median_days_to_resolve": median_days,
        "generated_at": utcnow().isoformat(),
    }
