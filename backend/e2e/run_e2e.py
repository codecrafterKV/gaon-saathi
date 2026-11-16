"""End-to-end browser test of the built Gaon Saathi app.

It starts an isolated server (temporary database and evidence folder, so your
development data is untouched), then drives a real browser through the full
journey: report a problem with a photo, save the codes, track the complaint,
sign in as an administrator, review and update the complaint, check the
tracking page again and add more information. It fails on any browser console
error, page error or Content-Security-Policy violation.

Requirements: `pip install -r requirements-dev.txt`, a built frontend
(`npm run build`), and Microsoft Edge or Google Chrome installed (or run
`python -m playwright install chromium` and set E2E_BROWSER_CHANNEL=chromium).

    python e2e/run_e2e.py [--screenshots DIR] [--headed]
"""

from __future__ import annotations

import argparse
import base64
import os
import re
import subprocess
import sys
import tempfile
import time
import urllib.request
from io import BytesIO
from pathlib import Path

BACKEND = Path(__file__).resolve().parent.parent
PORT = int(os.environ.get("E2E_PORT", "8765"))
BASE = f"http://127.0.0.1:{PORT}"
ADMIN_USER, ADMIN_PASS = "e2e.admin", "E2E-Strong-Passphrase-2026"
EXPECTED_HTTP_ERROR = re.compile(r"Failed to load resource: the server responded with a status of (401|404)")
ACCESS_LOG_LINE = re.compile(r"\d{1,3}(\.\d{1,3}){3}:\d+ - \"")


def make_env(tmp: Path) -> dict:
    env = dict(os.environ)
    env.update({
        "APP_ENV": "development",
        "DATABASE_URL": f"sqlite:///{(tmp / 'e2e.db').as_posix()}",
        "EVIDENCE_DIR": str(tmp / "evidence"),
        "SECRET_KEY": "e2e-secret-key-" + "x" * 40,
        "DATA_ENCRYPTION_KEY": base64.b64encode(os.urandom(32)).decode(),
        "POW_DIFFICULTY": os.environ.get("E2E_POW_DIFFICULTY", "16"),
        "RATE_LIMIT_ENABLED": "true",
        "SERVE_FRONTEND": "true",
    })
    return env


SETUP = f"""
from app.cli import cmd_migrate
cmd_migrate(None)
from app.database import get_sessionmaker
from app.models import AdminUser
from app.security.passwords import hash_password
from app.services.demo import seed_demo_data
with get_sessionmaker()() as db:
    db.add(AdminUser(username={ADMIN_USER!r}, role='admin', password_hash=hash_password({ADMIN_PASS!r})))
    db.commit()
    seed_demo_data(db, count=30)
print('setup ok')
"""


def gps_photo(path: Path) -> None:
    from PIL import Image

    img = Image.new("RGB", (1600, 1200), (60, 140, 80))
    exif = Image.Exif()
    exif[0x010F] = "E2E-PhoneMaker"
    exif[0x8825] = {1: "N", 2: (26.0, 51.0, 0.0), 3: "E", 4: (80.0, 56.0, 0.0)}
    img.save(path, "JPEG", exif=exif)


def wait_for_server(timeout=60):
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            with urllib.request.urlopen(f"{BASE}/api/health", timeout=2) as r:
                if r.status == 200:
                    return
        except Exception:  # noqa: BLE001
            time.sleep(0.5)
    raise RuntimeError("server did not start")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--screenshots", type=Path, default=None)
    parser.add_argument("--headed", action="store_true")
    args = parser.parse_args()
    shots = args.screenshots
    if shots:
        shots.mkdir(parents=True, exist_ok=True)

    from playwright.sync_api import expect, sync_playwright

    tmp = Path(tempfile.mkdtemp(prefix="gaon-e2e-"))
    env = make_env(tmp)
    subprocess.run([sys.executable, "-c", SETUP], cwd=BACKEND, env=env, check=True)
    photo = tmp / "IMG_20261101_my_phone.jpg"
    gps_photo(photo)

    server = subprocess.Popen(
        [sys.executable, "-m", "app.cli", "serve", "--port", str(PORT)], cwd=BACKEND, env=env,
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
    )
    problems: list[str] = []
    try:
        wait_for_server()
        with sync_playwright() as p:
            channel = os.environ.get("E2E_BROWSER_CHANNEL", "msedge")
            browser = p.chromium.launch(channel=None if channel == "chromium" else channel, headless=not args.headed)
            context = browser.new_context(viewport={"width": 1366, "height": 900}, accept_downloads=True)
            page = context.new_page()

            def on_console(msg):
                # Expected API answers (401 when signed out, 404 for a wrong tracking code)
                # are reported by the browser as resource errors; anything else is a problem.
                if msg.type == "error" and not EXPECTED_HTTP_ERROR.search(msg.text):
                    problems.append(f"console error on {page.url}: {msg.text[:300]}")
            page.on("console", on_console)
            page.on("pageerror", lambda exc: problems.append(f"page error on {page.url}: {exc}"))

            def shot(name, full=True):
                if shots:
                    if full:  # scroll through so scroll-triggered reveal animations run
                        height = page.evaluate("() => document.body.scrollHeight")
                        for _ in range(0, height, 500):
                            page.mouse.wheel(0, 500)
                            page.wait_for_timeout(60)
                        page.wait_for_timeout(800)
                        page.mouse.wheel(0, -height)
                        page.wait_for_timeout(200)
                    page.screenshot(path=str(shots / f"{name}.png"), full_page=full)

            def step(name):
                print(f"  - {name}")

            # ---------------- Public pages ----------------
            step("home page")
            page.goto(BASE + "/")
            expect(page.get_by_role("heading", level=1)).to_contain_text("Your Village.")
            expect(page.get_by_text("not an official government website")).to_be_visible()
            page.wait_for_timeout(600)
            shot("01-home")
            for path, text in [("/about", "raise their voice"), ("/how-it-works", "What each status means"),
                               ("/privacy", "How we protect you"), ("/terms", "Using Gaon Saathi"),
                               ("/contact", "How can we help"), ("/does-not-exist", "Page not found")]:
                step(f"page {path}")
                page.goto(BASE + path)
                expect(page.locator("main")).to_contain_text(text)
            shot("02-contact")

            # Header navigation links all work.
            page.goto(BASE + "/")
            for label, url in [("Track Complaint", "/track"), ("About Us", "/about"), ("How It Works", "/how-it-works"),
                               ("Contact / Support", "/contact")]:
                page.get_by_role("navigation", name="Main").get_by_role("link", name=label).click()
                expect(page).to_have_url(re.compile(re.escape(url) + "$"))

            # ---------------- Report a problem ----------------
            step("report form")
            page.goto(BASE + "/")
            page.get_by_role("link", name="Report a Problem").first.click()
            expect(page).to_have_url(re.compile("/report$"))
            page.get_by_role("button", name="Continue").click()
            expect(page.get_by_text("Please choose the type of problem.")).to_be_visible()
            page.get_by_text("Illegal Tree Cutting", exact=True).click()
            shot("03-report-category")
            page.get_by_role("button", name="Continue").click()

            page.get_by_role("button", name="Continue").click()  # empty details -> errors
            expect(page.get_by_text("Please enter the village name.")).to_be_visible()
            page.get_by_label("Village name").fill("Rampur Kalan")
            page.get_by_label("District").fill("Sitapur")
            page.get_by_label("State").select_option("Uttar Pradesh")
            page.get_by_label("Approximate location of the problem").fill("Canal road, near the pond")
            page.get_by_label("Describe the problem").fill(
                "Six neem trees on panchayat land were cut at night. Call me on 9876543210.")
            expect(page.get_by_text("may contain personal information")).to_be_visible()
            page.get_by_label("Describe the problem").fill(
                "Six neem trees on panchayat land near the canal road were cut at night last week and taken away.")
            shot("04-report-details")
            page.get_by_role("button", name="Continue").click()

            step("evidence upload")
            expect(page.get_by_text("Please do not upload photographs, videos, or documents containing your personal identity")).to_be_visible()
            page.locator("input[type=file]").set_input_files(str(photo))
            expect(page.get_by_text("Hidden location data removed")).to_be_visible(timeout=15000)
            expect(page.get_by_text("will be saved as evidence-1.jpg")).to_be_visible()
            shot("05-report-evidence")
            page.get_by_role("button", name="Continue").click()

            step("review and submit")
            submit = page.get_by_role("button", name="Submit Complaint")
            expect(submit).to_be_disabled()
            page.get_by_text("I understand that my complaint and supporting evidence may be reviewed").click()
            expect(page.get_by_text("Security check complete")).to_be_visible(timeout=60000)
            shot("06-report-review")
            submit.click()
            expect(page.get_by_text("Your complaint has been successfully submitted.")).to_be_visible(timeout=60000)
            complaint_id = page.get_by_test_id("complaint-id").inner_text().strip()
            token = page.get_by_test_id("tracking-code").inner_text().strip()
            assert re.match(r"^GS-\d{4}-[A-Z0-9]{8}$", complaint_id), complaint_id
            assert re.match(r"^([A-Z0-9]{4}-){3}[A-Z0-9]{4}$", token), token
            print(f"    submitted {complaint_id}")
            shot("07-success")
            with page.expect_download() as dl:
                page.get_by_role("button", name="Download as a text file").click()
            assert complaint_id in Path(dl.value.path()).read_text(encoding="utf-8")
            page.reload()
            expect(page.get_by_text("Nothing to show here")).to_be_visible()  # codes are not kept after refresh

            # ---------------- Track ----------------
            step("track complaint")
            page.goto(BASE + "/track")
            page.get_by_label("Complaint ID").fill(complaint_id)
            page.get_by_label("Secret Tracking Code").fill("2222-2222-2222-2222")
            page.get_by_role("button", name="Check status").click()
            expect(page.get_by_text("No complaint was found")).to_be_visible()
            page.get_by_label("Secret Tracking Code").fill(token.lower().replace("-", ""))
            page.get_by_role("button", name="Check status").click()
            expect(page.get_by_text("Progress update")).to_be_visible()
            expect(page.locator("main")).not_to_contain_text("neem trees")
            shot("08-track-received")

            # ---------------- Admin ----------------
            step("admin login")
            page.goto(BASE + "/admin")
            expect(page).to_have_url(re.compile("/admin/login$"))
            page.get_by_label("Username").fill(ADMIN_USER)
            page.get_by_label("Password", exact=True).fill("wrong-password-123")
            page.get_by_role("button", name="Sign in").click()
            expect(page.get_by_text("Incorrect username or password")).to_be_visible()
            shot("09-admin-login")
            page.get_by_label("Password", exact=True).fill(ADMIN_PASS)
            page.get_by_role("button", name="Sign in").click()
            expect(page.get_by_text("Total complaints received")).to_be_visible()
            expect(page.get_by_text("Complaints by category")).to_be_visible()
            page.wait_for_timeout(1200)
            shot("10-dashboard")
            total = page.locator("a", has_text="Total complaints received").locator("p").nth(1).inner_text()
            assert total.strip() == "31", f"expected 31 complaints (30 demo + 1 live), got {total}"
            page.get_by_role("radio", name="Live only").click()
            expect(page.locator("a", has_text="Total complaints received").locator("p").nth(1)).to_have_text("1")
            page.get_by_role("radio", name="All data").click()
            page.get_by_role("button", name="Table").first.click()
            expect(page.locator("table").first).to_be_visible()

            step("complaint list and filters")
            page.get_by_role("navigation", name="Admin").get_by_role("link", name="Complaints").click()
            expect(page.get_by_text("complaints found").or_(page.get_by_text("complaint found"))).to_be_visible()
            page.get_by_placeholder("Search complaint ID, village or district").fill(complaint_id)
            expect(page.get_by_text("1 complaint found")).to_be_visible()
            shot("11-complaints")
            page.get_by_role("link", name="Open").first.click()

            step("complaint detail and evidence")
            expect(page.get_by_text("Six neem trees on panchayat land")).to_be_visible()
            img = page.locator("img[alt='evidence-1.jpg']")
            expect(img).to_be_visible()
            for _ in range(40):  # strict CSP forbids eval-based wait_for_function, so poll instead
                if img.evaluate("el => el.complete && el.naturalWidth") > 0:
                    break
                page.wait_for_timeout(250)
            else:
                problems.append("evidence image did not load in the admin view")
            expect(page.get_by_text("Metadata removed")).to_be_visible()
            shot("12-detail")

            step("status workflow")
            page.get_by_label("New status").select_option("under_review")
            page.get_by_label("Internal explanation *").fill("Checked details, location is clear.")
            page.get_by_label("Public progress message").fill("Our team has started reviewing your complaint.")
            page.get_by_role("button", name="Update status").click()
            expect(page.get_by_text("Status updated.")).to_be_visible()
            page.get_by_role("tab", name="Verify").click()
            page.get_by_label("Verification result").select_option("verified")
            page.get_by_label("Findings").fill("Photo shows fresh stumps at the described location.")
            page.get_by_role("button", name="Save verification").click()
            expect(page.get_by_text("Verification saved.")).to_be_visible()
            page.get_by_role("tab", name="Ask").click()
            page.get_by_label("Internal reason *").fill("Need a wider photo of the site.")
            page.get_by_role("button", name="Request more information").click()
            expect(page.get_by_text("Request sent.")).to_be_visible()
            shot("13-detail-updated")

            step("tracking shows update and reporter adds info")
            page.goto(BASE + "/track")
            page.get_by_label("Complaint ID").fill(complaint_id)
            page.get_by_label("Secret Tracking Code").fill(token)
            page.get_by_role("button", name="Check status").click()
            expect(page.get_by_text("Our team has asked for more information")).to_be_visible()
            expect(page.get_by_text("Under Review", exact=True).first).to_be_visible()
            page.get_by_label("Message").fill("The cutting continued on Sunday near the same spot.")
            page.get_by_role("button", name="Send information").click()
            expect(page.get_by_text("Thank you. Your information was added")).to_be_visible(timeout=60000)
            shot("14-track-updated")

            step("admin pages")
            page.goto(BASE + f"/admin/complaints/{complaint_id}")
            expect(page.get_by_text("The cutting continued on Sunday")).to_be_visible()
            for path, text in [("/admin/authorities", "Authorities and departments"), ("/admin/audit", "Audit log"),
                               ("/admin/settings", "Security status")]:
                page.goto(BASE + path)
                expect(page.locator("main")).to_contain_text(text)
            shot("15-settings")
            page.goto(BASE + "/admin/audit")
            expect(page.locator("table")).to_contain_text("complaint.status_changed")
            shot("16-audit")

            step("mobile layout")
            mobile = browser.new_context(viewport={"width": 390, "height": 844}, device_scale_factor=2, is_mobile=True, has_touch=True)
            mpage = mobile.new_page()
            mpage.on("console", lambda m: m.type == "error" and not EXPECTED_HTTP_ERROR.search(m.text)
                     and problems.append(f"mobile console error: {m.text[:300]}"))
            mpage.goto(BASE + "/")
            mpage.get_by_role("button", name="Open menu").click()
            expect(mpage.get_by_role("navigation", name="Mobile")).to_be_visible()
            mpage.get_by_role("navigation", name="Mobile").get_by_role("link", name="Report a Problem").click()
            expect(mpage).to_have_url(re.compile("/report$"))
            overflow = mpage.evaluate("document.documentElement.scrollWidth > window.innerWidth")
            assert not overflow, "horizontal overflow on mobile"
            if shots:
                mpage.goto(BASE + "/")
                mpage.wait_for_timeout(500)
                mpage.screenshot(path=str(shots / "17-mobile-home.png"), full_page=False)
                mpage.goto(BASE + "/report")
                mpage.screenshot(path=str(shots / "18-mobile-report.png"), full_page=False)

            step("logout")
            page.goto(BASE + "/admin")
            page.get_by_role("button", name="Sign out").first.click()
            expect(page).to_have_url(re.compile("/admin/login$"))
            page.goto(BASE + "/admin/complaints")
            expect(page).to_have_url(re.compile("/admin/login$"))
            browser.close()
    finally:
        server.terminate()
        try:
            out = server.communicate(timeout=10)[0].decode("utf-8", "replace")
        except subprocess.TimeoutExpired:
            server.kill()
            out = ""
    # The server log must not contain client addresses (access logs), requests or complaint text.
    print("\nServer log:\n" + "\n".join("  | " + line for line in out.splitlines()))
    if ACCESS_LOG_LINE.search(out):
        problems.append("server log contains an access-log line with a client address")
    for needle in ("neem", "Rampur Kalan", '"GET ', '"POST '):
        if needle in out:
            problems.append(f"server log contains {needle!r}")
    if problems:
        print("\nPROBLEMS:")
        for prob in problems:
            print("  *", prob)
        return 1
    print("\nEnd-to-end test passed: no console errors, no CSP violations, logs clean.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
