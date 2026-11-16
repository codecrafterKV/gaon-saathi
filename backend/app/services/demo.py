"""DEMO DATA generator.

Every record created here is flagged ``is_demo=True``, uses complaint IDs of
the form ``GS-DEMO-XXXXXXXX`` and is shown with a DEMO badge in the admin
dashboard, so it can never be confused with real complaints. Village names
are illustrative and the complaints are fictional; no real person is named.

Running the seeder again first removes the previous demo data.
"""

from __future__ import annotations

import random
from datetime import date, timedelta
from io import BytesIO

from PIL import Image, ImageDraw, ImageFont
from sqlalchemy.orm import Session

from app.constants import CATEGORIES, DEFAULT_PUBLIC_MESSAGES
from app.db_types import utcnow
from app.models import Authority, ComplaintForwarding, ComplaintNote, ComplaintStatusHistory
from app.schemas import ComplaintCreate
from app.services.complaints import create_complaint
from app.services.evidence import process_upload
from app.services.maintenance import clear_demo_data

VILLAGES = [
    ("Rampur Kalan", "Sitapur", "Uttar Pradesh"),
    ("Sonpur Khurd", "Barabanki", "Uttar Pradesh"),
    ("Chandanpur", "Gaya", "Bihar"),
    ("Basantpur", "Muzaffarpur", "Bihar"),
    ("Kishanpura", "Sehore", "Madhya Pradesh"),
    ("Pipariya Tola", "Vidisha", "Madhya Pradesh"),
    ("Devli Kheda", "Tonk", "Rajasthan"),
    ("Ramsar", "Ajmer", "Rajasthan"),
    ("Shivnagar Wadi", "Nashik", "Maharashtra"),
    ("Ambewadi", "Jalna", "Maharashtra"),
    ("Haripur", "Ganjam", "Odisha"),
    ("Dhanpur", "Kalahandi", "Odisha"),
    ("Tilaiya Tola", "Gumla", "Jharkhand"),
    ("Navagaon", "Raipur", "Chhattisgarh"),
]

DESCRIPTIONS = {
    "public_space_encroachment": [
        "A permanent shop has been built on the common land next to the village pond. The path to the pond is now "
        "blocked and cattle cannot reach the water. The construction started about two months ago.",
        "The main village lane near the primary school has been narrowed by a new boundary wall. School children now "
        "have to walk on the drain cover. Ambulances cannot enter this lane.",
        "Part of the cremation ground land has been fenced and is being used for private farming since last season.",
    ],
    "illegal_tree_cutting": [
        "Six large neem trees on the panchayat land beside the canal road were cut at night last week. The wood was "
        "loaded on a tractor. Nobody has shown any permission letter.",
        "Trees planted under the plantation drive near the community hall are being cut one by one and sold as firewood.",
        "Old banyan tree near the bus stop was cut down without any notice. Branches are still lying on the road.",
    ],
    "development_fund_misuse": [
        "The board says a community toilet block was built in our ward with government funds, but no toilet exists at "
        "the location. Only the foundation was laid and work stopped.",
        "The new CC road in the village was laid only half the length shown on the work board. The road is already "
        "breaking after one rain.",
        "Payments for the village pond deepening work were shown as complete but the pond was never deepened.",
    ],
    "road_drainage": [
        "The drain beside the main road is fully blocked for three months. Dirty water enters houses during rain and "
        "mosquitoes have increased. Many children have fever.",
        "The culvert near the field road collapsed. Farmers cannot take tractors to the fields and the school van has "
        "stopped coming.",
        "Big potholes on the road from the village to the health centre. Two accidents happened last month.",
    ],
    "ration_distribution": [
        "The ration shop gives 4 kg instead of 5 kg per person but the machine slip shows the full quantity. The shop "
        "opens only two days a month.",
        "Several elderly people are told their thumb impression does not match and they are sent back without ration "
        "for the last two months.",
        "Rice given at the ration shop this month was of very poor quality with stones and insects.",
    ],
    "public_resource_misuse": [
        "The panchayat water tanker is being used for private construction work instead of supplying drinking water to "
        "the lower hamlet.",
        "The community hall is locked and used as a private godown. Village meetings cannot be held there.",
        "Street lights bought for the village were installed at a private farmhouse instead of the main lane.",
    ],
    "corruption_governance": [
        "Gram Sabha meetings have not been held for over a year but the register shows meetings with signatures.",
        "People are being asked to pay money to get their names added to the housing scheme list.",
        "Job cards of many workers are kept with a middleman and wages are withdrawn without the workers' knowledge.",
    ],
    "other": [
        "The hand pump near the Anganwadi centre has been broken for weeks. Women walk 2 km for drinking water.",
        "The village primary health sub-centre is closed most days and medicines are not available.",
        "The solar pump installed for irrigation is not working and no one has come to repair it.",
    ],
}

LOCATIONS = [
    "Near the village pond", "Ward 3, behind the primary school", "Main road near the bus stop",
    "Next to the panchayat bhawan", "Canal road, east side of the village", None, None,
    "Near the Anganwadi centre", "Lower hamlet, near the temple", None,
]

AUTHORITIES = [
    dict(name="Centralised Public Grievance Redress and Monitoring System (CPGRAMS)",
         department="Department of Administrative Reforms and Public Grievances, Government of India",
         level="national", grievance_channel="Online grievance portal", website="https://pgportal.gov.in",
         notes="Real national grievance portal (included in demo data as a reference). "
               "Always check the current procedure on the official website before use."),
    dict(name="Block Development Office (DEMO)", department="Rural Development", level="block",
         grievance_channel="Written application", notes="DEMO record - replace with real office details."),
    dict(name="District Supply Office (DEMO)", department="Food and Civil Supplies", level="district",
         grievance_channel="Written application / helpline", notes="DEMO record - replace with real office details."),
    dict(name="Divisional Forest Office (DEMO)", department="Forest Department", level="district",
         grievance_channel="Written application", notes="DEMO record - replace with real office details."),
    dict(name="Gram Panchayat Office (DEMO)", department="Panchayati Raj", level="gram_panchayat",
         grievance_channel="Gram Sabha / written application", notes="DEMO record - replace with real office details."),
    dict(name="Rural Works Division (DEMO)", department="Public Works / Rural Engineering", level="district",
         grievance_channel="Written application", notes="DEMO record - replace with real office details."),
    dict(name="District Collector's Grievance Cell (DEMO)", department="District Administration", level="district",
         grievance_channel="Public hearing / written application", notes="DEMO record - replace with real office details."),
]

CATEGORY_AUTHORITY = {
    "public_space_encroachment": 1, "illegal_tree_cutting": 3, "development_fund_misuse": 1,
    "road_drainage": 5, "ration_distribution": 2, "public_resource_misuse": 4,
    "corruption_governance": 6, "other": 0,
}

PATHS = [
    (["received"], 7),
    (["received", "under_review"], 6),
    (["received", "under_review", "evidence_verification"], 5),
    (["received", "under_review", "action_in_progress"], 4),
    (["received", "under_review", "evidence_verification", "forwarded"], 5),
    (["received", "under_review", "action_in_progress", "forwarded", "resolved"], 4),
    (["received", "under_review", "evidence_verification", "action_in_progress", "resolved"], 2),
    (["received", "under_review", "rejected"], 2),
    (["received", "under_review", "evidence_verification", "forwarded", "closed"], 1),
    (["received", "closed"], 1),
]

NOTES = {
    "under_review": "[DEMO] Complaint read by the review team. Location and category look correct.",
    "evidence_verification": "[DEMO] Checking the photographs and comparing with public work records.",
    "action_in_progress": "[DEMO] Identified the responsible department. Preparing an application.",
    "forwarded": "[DEMO] Application submitted to the authority. Acknowledgement received.",
    "resolved": "[DEMO] Field update received: the issue has been addressed.",
    "rejected": "[DEMO] Not enough information to take this forward and the reporter did not add more details.",
    "closed": "[DEMO] Duplicate of an earlier complaint about the same issue.",
}


def _demo_image(label: str, seed: int) -> bytes:
    rng = random.Random(seed)
    img = Image.new("RGB", (1280, 860))
    draw = ImageDraw.Draw(img)
    sky = (rng.randint(150, 190), rng.randint(195, 225), 240)
    for y in range(520):
        t = y / 520
        draw.line([(0, y), (1280, y)], fill=(int(sky[0] + 60 * t), int(sky[1] + 25 * t), 245))
    draw.rectangle([0, 520, 1280, 860], fill=(118, 150, 92))
    draw.polygon([(520, 860), (760, 860), (660, 520), (620, 520)], fill=(170, 150, 120))
    for x in range(80, 1280, rng.randint(170, 230)):
        if 470 < x < 800:
            continue
        h = rng.randint(140, 220)
        draw.rectangle([x - 8, 520 - h // 3, x + 8, 540], fill=(92, 64, 40))
        draw.ellipse([x - 60, 520 - h, x + 60, 520 - h // 3 + 30], fill=(46, 120, 66))
    draw.rectangle([0, 0, 1280, 120], fill=(11, 31, 58))
    try:
        font_big = ImageFont.load_default(size=54)
        font_small = ImageFont.load_default(size=30)
    except TypeError:  # very old Pillow
        font_big = font_small = ImageFont.load_default()
    draw.text((40, 26), "DEMO EVIDENCE - SAMPLE IMAGE", fill=(255, 255, 255), font=font_big)
    draw.rectangle([0, 780, 1280, 860], fill=(0, 0, 0))
    draw.text((40, 800), f"Gaon Saathi demo data | {label}", fill=(220, 220, 220), font=font_small)
    out = BytesIO()
    img.save(out, format="JPEG", quality=82)
    return out.getvalue()


def seed_demo_data(db: Session, count: int = 36, seed: int = 2026) -> dict:
    clear_demo_data(db)
    rng = random.Random(seed)

    authorities = [Authority(is_demo=True, **a) for a in AUTHORITIES]
    db.add_all(authorities)
    db.commit()

    paths = [p for p, w in PATHS for _ in range(w)]
    categories = list(CATEGORIES)
    now = utcnow()
    tracking: list[dict] = []
    image_cache: dict[str, object] = {}

    for i in range(count):
        category = categories[i % len(categories)] if i < len(categories) else rng.choice(categories)
        village, district, state = rng.choice(VILLAGES)
        path = rng.choice(paths)
        age_days = rng.randint(len(path) * 6, 175) if len(path) > 1 else rng.randint(0, 20)
        submitted = now - timedelta(days=age_days, hours=rng.randint(0, 23), minutes=rng.randint(0, 59))

        files = []
        if rng.random() < 0.4:
            if category not in image_cache:
                image_cache[category] = process_upload("demo.jpg", _demo_image(CATEGORIES[category], i))
            files.append(image_cache[category])

        data = ComplaintCreate(
            category=category, village=village, district=district, state=state,
            description="[DEMO DATA] " + rng.choice(DESCRIPTIONS[category]),
            approximate_location=rng.choice(LOCATIONS),
        )
        complaint, token = create_complaint(db, data, files, is_demo=True, submitted_at=submitted)
        tracking.append({"complaint_id": complaint.public_id, "tracking_token": token, "status": path[-1]})

        # Replay a realistic workflow history.
        when = submitted
        complaint.history[0].internal_note = "[DEMO] Complaint submitted through the public form."
        authority = authorities[CATEGORY_AUTHORITY[category]]
        for previous, status in zip(path, path[1:]):
            when = min(when + timedelta(days=rng.randint(1, 9), hours=rng.randint(1, 8)), now - timedelta(hours=1))
            public_message = DEFAULT_PUBLIC_MESSAGES[status] if rng.random() < 0.5 else None
            complaint.history.append(ComplaintStatusHistory(
                from_status=previous, to_status=status, internal_note=NOTES[status],
                public_message=public_message, changed_at=when,
            ))
            complaint.status = status
            complaint.public_message = public_message
            complaint.updated_at = when
            if status == "evidence_verification":
                complaint.verification_status = "verified" if files else rng.choice(["verified", "unverified", "pending"])
                complaint.notes.append(ComplaintNote(kind="verification", created_at=when,
                                                     body="[DEMO] Photographs match the described location."
                                                     if files else "[DEMO] Checked public records for the work."))
            if status == "forwarded":
                complaint.authority_id = authority.id
                complaint.verification_status = "verified"
                complaint.forwardings.append(ComplaintForwarding(
                    authority_id=authority.id, authority_name=authority.name,
                    channel="online_portal" if authority.level == "national" else "letter",
                    submitted_on=when.date() if when.date() <= date.today() else date.today(),
                    reference_number=f"DEMO-ACK-{rng.randint(10000, 99999)}",
                    acknowledgement_details="[DEMO] Acknowledgement slip received at the office counter.",
                    created_at=when,
                ))
            if status == "resolved":
                complaint.resolution_summary = ("[DEMO] The department confirmed the work was completed and a "
                                                "village volunteer shared a photo of the repaired site.")
            if status in ("resolved", "rejected", "closed"):
                complaint.closed_at = when
        if len(path) > 2 and rng.random() < 0.5:
            complaint.notes.append(ComplaintNote(kind="follow_up", created_at=when,
                                                 body="[DEMO] Called the office for an update; told the file is in process."))
        if path[-1] in ("under_review", "evidence_verification") and rng.random() < 0.3:
            complaint.info_requested = True
            complaint.verification_status = "needs_more_info"
            complaint.public_message = "Please add a photo of the problem site, if it is safe for you to do so."
        db.commit()

    return {"complaints": count, "authorities": len(authorities), "sample_tracking": tracking}
