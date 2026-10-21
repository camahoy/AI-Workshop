"""End-to-end browser check against a running app (not part of pytest).

    streamlit run pa_boards/app.py --server.port 8600   # with PRESENTER_PASSCODE set
    python pa_boards/tests/browser_check.py http://localhost:8600 test-pass OUT_DIR

Drives a 360px phone through Board A (post, vote, undo, comment) and
Board C, checks the presenter view picks the post up, hides it, reveals
Board C, and saves screenshots to OUT_DIR.
"""
import os
import sys
import time
from pathlib import Path

from playwright.sync_api import expect, sync_playwright

BASE, PASS, OUT = sys.argv[1], sys.argv[2], Path(sys.argv[3])
OUT.mkdir(parents=True, exist_ok=True)
PHONE = {"viewport": {"width": 360, "height": 780}, "device_scale_factor": 2, "is_mobile": True, "has_touch": True}


def wait_app(page):
    page.wait_for_selector("text=Board", timeout=20000)
    time.sleep(1.5)


with sync_playwright() as p:
    browser = p.chromium.launch(executable_path=os.environ.get("CHROMIUM_PATH") or None)

    # ---- presenter unlock
    pres = browser.new_context(viewport={"width": 1920, "height": 1080}).new_page()
    pres.goto(f"{BASE}/?board=a&view=present")
    pres.locator("input[type=password]").fill(PASS)
    pres.get_by_role("button", name="Unlock").click()
    expect(pres.get_by_text("Board A controls")).to_be_visible(timeout=15000)

    # ---- participant on a phone
    phone = browser.new_context(**PHONE).new_page()
    phone.goto(f"{BASE}/?board=a")
    wait_app(phone)
    expect(phone.get_by_text("Describe the task, not the client.").first).to_be_visible()
    phone.locator("textarea").first.fill("Turning long Teams threads into a short summary")
    phone.get_by_role("button", name="Post", exact=True).click()
    vote = phone.get_by_role("button", name="▲ I do this too · 0")
    expect(vote).to_be_visible(timeout=10000)
    vote.click()
    expect(phone.get_by_role("button", name="✓ I do this too · 1  (tap to undo)")).to_be_visible(timeout=10000)
    phone.get_by_role("button", name="✓ I do this too · 1  (tap to undo)").click()
    expect(phone.get_by_role("button", name="▲ I do this too · 0")).to_be_visible(timeout=10000)
    phone.get_by_role("button", name="▲ I do this too · 0").click()
    expect(phone.get_by_role("button", name="✓ I do this too · 1  (tap to undo)")).to_be_visible(timeout=10000)
    phone.get_by_role("button", name="💬 Comments (0)").first.click()
    phone.get_by_role("textbox", name="Add a comment").fill("Same, saves me an hour a week")
    phone.get_by_role("button", name="Add comment").click()
    expect(phone.get_by_text("Same, saves me an hour a week")).to_be_visible(timeout=10000)
    phone.screenshot(path=str(OUT / "phone-board-a.png"), full_page=True)
    width = phone.evaluate("document.documentElement.scrollWidth")
    assert width <= 360, f"horizontal scroll on phone: {width}px"

    # ---- presenter sees it live, without reload
    t0 = time.time()
    expect(pres.locator(".pp-card", has_text="Turning long Teams threads into a short summary")).to_be_visible(timeout=10000)
    print(f"presenter picked up post in {time.time() - t0:.1f}s")
    pres.get_by_role("button", name="Generate summary", exact=True).click()
    expect(pres.get_by_text("Top 5 by votes")).to_be_visible(timeout=10000)
    pres.screenshot(path=str(OUT / "presenter-board-a.png"))

    # ---- moderation hide
    pres.get_by_text("Moderate (hide a post or comment)").click()
    pres.get_by_role("button", name="Hide post: Turning long Teams threads").click()
    expect(pres.locator(".pp-card", has_text="Turning long Teams threads")).to_have_count(0, timeout=10000)
    phone.get_by_role("button", name="↻ Refresh").click()  # phones redraw on tap, or every 30 s
    expect(phone.locator(".pa-post", has_text="Turning long Teams threads")).to_have_count(0, timeout=15000)
    print("hidden post gone from presenter and phone")

    # ---- Board C
    phone.goto(f"{BASE}/?board=c")
    wait_app(phone)
    phone.get_by_role("button", name="☐  Use case showcases").click()
    expect(phone.get_by_role("button", name="☑  Use case showcases")).to_be_visible(timeout=10000)
    phone.get_by_role("button", name="☐  Privacy and data Q&A").click()
    expect(phone.get_by_role("button", name="☑  Privacy and data Q&A")).to_be_visible(timeout=10000)
    expect(phone.get_by_text("Vote counts appear here when the presenter reveals them.")).to_be_visible()
    pres.goto(f"{BASE}/?board=c&view=present")
    expect(pres.get_by_text("1 person has voted")).to_be_visible(timeout=15000)
    pres.get_by_role("button", name="Reveal results", exact=True).click()
    expect(pres.get_by_text("1 vote · 100%").first).to_be_visible(timeout=10000)
    phone.get_by_role("button", name="↻ Refresh").click()
    expect(phone.get_by_text("Results · 1 person")).to_be_visible(timeout=15000)
    pres.screenshot(path=str(OUT / "presenter-board-c.png"))
    phone.screenshot(path=str(OUT / "phone-board-c.png"), full_page=True)

    # ---- Board B with seeds, phone
    phone.goto(f"{BASE}/?board=b")
    wait_app(phone)
    expect(phone.get_by_text("From the 13 Aug session (other service lines)").first).to_be_visible()
    phone.screenshot(path=str(OUT / "phone-board-b.png"), full_page=True)
    pres.goto(f"{BASE}/?board=b&view=present")
    # New page = new session: the passcode cookie, not session state, must
    # carry the presenter in. Wait for the real board, not a stale sidebar.
    expect(pres.locator(".pp-question", has_text="Where does your time go")).to_be_visible(timeout=20000)
    expect(pres.locator(".pp-card")).to_have_count(6, timeout=10000)  # the seed rows
    time.sleep(1)
    pres.screenshot(path=str(OUT / "presenter-board-b.png"))

    browser.close()
    print("browser check passed")
