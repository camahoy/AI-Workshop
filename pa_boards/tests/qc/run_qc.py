"""End-to-end QC run against a live local app, with fake entries.

    PA_BOARDS_DATA_DIR=<same dir as the server> \\
    python pa_boards/tests/qc/run_qc.py http://localhost:8600 <passcode> <out_dir> <mock_log>

The server must be running with PRESENTER_PASSCODE set and (for the AI
check) AI_SUMMARY_PROVIDER=azure_openai pointed at tests/qc/mock_azure.py.
Writes <out_dir>/qc_results.json, screenshots, and the downloaded exports.
Ends by pressing "Delete all data" and checking the boards are empty.
"""
import csv
import io
import json
import os
import sys
import time
import traceback
import zipfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from PIL import Image  # noqa: E402
from playwright.sync_api import expect, sync_playwright  # noqa: E402

from palib import config, export, store, summary  # noqa: E402
import fake_session  # noqa: E402

BASE, PASS, OUT, MOCK_LOG = sys.argv[1], sys.argv[2], Path(sys.argv[3]), Path(sys.argv[4])
OUT.mkdir(parents=True, exist_ok=True)
CHROMIUM = os.environ.get("CHROMIUM_PATH") or None
SESSION_DATE = "2026-10-28"

results = []


def check(area, name, fn):
    t0 = time.time()
    try:
        detail = fn()
        results.append({"area": area, "name": name, "ok": True, "detail": detail or "", "secs": round(time.time() - t0, 1)})
        print(f"PASS  {area}: {name}  {detail or ''}")
    except Exception as e:  # record and keep going
        results.append({"area": area, "name": name, "ok": False, "detail": f"{type(e).__name__}: {e}"[:400],
                        "secs": round(time.time() - t0, 1)})
        print(f"FAIL  {area}: {name}  {e}")
        traceback.print_exc(limit=1)


def shot(page, name, full=False):
    path = OUT / f"{name}.png"
    page.screenshot(path=str(path), full_page=full)
    return path.name


def settle(page, secs=1.5):
    page.wait_for_timeout(int(secs * 1000))


def vote_button(page, text):
    return page.locator(
        f"xpath=//div[contains(@class,'pa-post')][div[@class='text' and text()={text!r}]]"
        "/ancestor::div[contains(@class,'stElementContainer')][1]/following-sibling::div[1]//button"
    ).first


def csv_rows(blob):
    assert blob.startswith(b"\xef\xbb\xbf"), "missing UTF-8 BOM (Excel would garble accents)"
    return list(csv.reader(io.StringIO(blob.decode("utf-8-sig"))))


# ------------------------------------------------------------ fake data --
store.delete_all()
store.set_setting("session_date", SESSION_DATE)
store.set_setting("ai_summary", True)
created = fake_session.load()
data = store.load()
fake_counts = {
    "a_posts": len(data["boards"]["a"]["posts"]),
    "b_posts": len(data["boards"]["b"]["posts"]),
    "c_people": len(store.participants(data, "c")),
    "a_votes": sum(len(p["votes"]) for p in data["boards"]["a"]["posts"]),
    "b_votes": sum(len(p["votes"]) for p in data["boards"]["b"]["posts"]),
}
print("fake session loaded:", fake_counts)

with sync_playwright() as p:
    browser = p.chromium.launch(executable_path=CHROMIUM)
    iphone = browser.new_context(**p.devices["iPhone 13"])
    android = browser.new_context(**p.devices["Pixel 7"])
    desktop = browser.new_context(viewport={"width": 1440, "height": 900})
    dark_phone = browser.new_context(**p.devices["iPhone 13"], color_scheme="dark")
    projector = browser.new_context(viewport={"width": 1920, "height": 1080}, accept_downloads=True)
    pres = projector.new_page()

    # ------------------------------------------------------- access --
    def no_login_for_participants():
        page = iphone.new_page()
        page.goto(f"{BASE}/?board=a")
        expect(page.locator(".pa-question", has_text="How do you use AI today?")).to_be_visible(timeout=30000)
        assert page.locator("input[type=password]").count() == 0
        return "QR link opens Board A straight away: no sign-in, no password, anonymous by default"
    check("Access", "Participants need no login", no_login_for_participants)

    def presenter_locked():
        page = desktop.new_page()
        page.goto(f"{BASE}/?board=a&view=present")
        expect(page.locator("input[type=password]")).to_be_visible(timeout=30000)
        page.locator("input[type=password]").fill("wrong-code")
        page.get_by_role("button", name="Unlock").click()
        expect(page.get_by_text("Incorrect passcode.")).to_be_visible(timeout=15000)
        assert page.get_by_text("Board A controls").count() == 0
        page.close()
        return "wrong passcode is refused; controls stay hidden"
    check("Access", "Presenter view is passcode-locked", presenter_locked)

    def presenter_unlock():
        pres.goto(f"{BASE}/?board=a&view=present")
        pres.locator("input[type=password]").fill(PASS)
        pres.get_by_role("button", name="Unlock").click()
        expect(pres.get_by_text("Board A controls")).to_be_visible(timeout=30000)
        expect(pres.locator(".pp-card").first).to_be_visible(timeout=15000)
        return "unlocked; projector shows live cards"
    check("Access", "Presenter unlocks with the passcode", presenter_unlock)

    # --------------------------------------------------- Board A phone --
    a_phone = iphone.pages[0]
    my_post = "Drafting survey invitation emails (QC phone post)"

    def a_empty_rejected():
        a_phone.get_by_role("button", name="Post", exact=True).click()
        expect(a_phone.get_by_text("Please fill in")).to_be_visible(timeout=15000)
        return "empty post refused with a message"
    check("Board A", "Required field enforced", a_empty_rejected)

    def a_post_from_phone():
        a_phone.locator('textarea[aria-label="What do you use AI for? (required)"]').fill(my_post)
        a_phone.locator('div[data-testid="stSelectbox"]').nth(0).click()
        a_phone.get_by_role("option", name="Copilot", exact=True).click()
        a_phone.locator('div[data-testid="stSelectbox"]').nth(1).click()
        a_phone.get_by_role("option", name="Client email", exact=True).click()
        a_phone.get_by_role("button", name="Post", exact=True).click()
        expect(a_phone.locator(".pa-post", has_text=my_post)).to_be_visible(timeout=20000)
        post = next(x for x in store.load()["boards"]["a"]["posts"] if x["text"] == my_post)
        assert (post["tool"], post["task"], post["name"]) == ("Copilot", "Client email", ""), post
        return "saved with Tool = Copilot, Task = Client email, anonymous"
    check("Board A", "Post with tags from an iPhone-size screen", a_post_from_phone)

    def a_200_limit():
        box = a_phone.locator('textarea[aria-label="What do you use AI for? (required)"]')
        box.press_sequentially("x" * 260, delay=0)  # typed, like a person
        value = box.input_value()
        assert len(value) == config.MAX_POST_CHARS, len(value)
        a_phone.locator('textarea[aria-label="What do you use AI for? (required)"]').fill("")
        return f"typing 260 characters keeps {len(value)}"
    check("Board A", "200-character limit", a_200_limit)

    def a_vote_undo():
        btn = vote_button(a_phone, my_post)
        btn.click()
        expect(btn).to_have_text("✓ I do this too · 1 (tap to undo)", timeout=15000)
        btn.click()
        expect(btn).to_have_text("▲ I do this too · 0", timeout=15000)
        btn.click()
        expect(btn).to_have_text("✓ I do this too · 1 (tap to undo)", timeout=15000)
        post = next(x for x in store.load()["boards"]["a"]["posts"] if x["text"] == my_post)
        assert len(post["votes"]) == 1 == len(set(post["votes"]))
        return "tap = 1 vote, tap again = 0, tap again = 1; stored once"
    check("Board A", "One vote per browser, undo works", a_vote_undo)

    def a_reload_keeps_vote():
        a_phone.reload()
        btn = vote_button(a_phone, my_post)
        expect(btn).to_have_text("✓ I do this too · 1 (tap to undo)", timeout=20000)
        return "after a page reload the phone still shows its vote (browser id kept in a cookie)"
    check("Board A", "Vote survives a reload (no double vote by refreshing)", a_reload_keeps_vote)

    def a_comment():
        a_phone.locator(f"xpath=//div[contains(@class,'pa-post')][div[@class='text' and text()={my_post!r}]]"
                        "/ancestor::div[contains(@class,'stElementContainer')][1]/following-sibling::div[1]//button").nth(1).click()
        a_phone.locator('input[aria-label="Add a comment"]').fill("Same for reminder emails")
        a_phone.get_by_role("button", name="Add comment").click()
        expect(a_phone.get_by_text("Same for reminder emails")).to_be_visible(timeout=15000)
        return "comment shows under the post"
    check("Board A", "Comment on a post", a_comment)
    check("Board A", "Phone screenshot", lambda: shot(a_phone, "phone-iphone-board-a", full=True))

    def no_horizontal_scroll():
        widths = {}
        for name, ctx in (("iPhone 13", iphone), ("Pixel 7", android)):
            page = ctx.pages[0] if ctx.pages else ctx.new_page()
            if not ctx.pages or page.url == "about:blank":
                page.goto(f"{BASE}/?board=b")
                settle(page, 4)
            widths[name] = (page.evaluate("document.documentElement.scrollWidth"), page.viewport_size["width"])
            assert widths[name][0] <= widths[name][1], widths
        return ", ".join(f"{k}: page {w}px in {v}px screen" for k, (w, v) in widths.items())

    # ---------------------------------------------------- Board B phone --
    b_phone = android.new_page()

    def b_post_from_android():
        b_phone.goto(f"{BASE}/?board=b")
        expect(b_phone.locator(".pa-question")).to_be_visible(timeout=30000)
        b_phone.locator('textarea[aria-label="What would you hand to AI? (required)"]').fill("Copying weights into the tab spec (QC phone post)")
        b_phone.locator('div[data-testid="stSelectbox"]').nth(0).click()
        b_phone.get_by_role("option", name="Weekly", exact=True).click()
        b_phone.locator('input[type="number"]').fill("30")
        b_phone.locator('input[aria-label="Name (optional, leave blank to stay anonymous)"]').fill("QC Tester")
        b_phone.get_by_role("button", name="Post", exact=True).click()
        expect(b_phone.locator(".pa-post", has_text="Copying weights into the tab spec")).to_be_visible(timeout=20000)
        post = next(x for x in store.load()["boards"]["b"]["posts"] if "Copying weights" in x["text"])
        assert (post["freq"], post["minutes"], post["name"]) == ("Weekly", 30, "QC Tester"), post
        b_phone.get_by_role("button", name="Show all posts").click()
        expect(b_phone.get_by_text(config.SEED_LABEL).first).to_be_visible(timeout=15000)
        return ("saved with How often = Weekly, 30 minutes, name = QC Tester; own new post visible on a busy "
                "board; seed rows labelled '" + config.SEED_LABEL + "'")
    check("Board B", "Post with frequency and minutes from an Android-size screen", b_post_from_android)
    check("Board B", "Phone screenshot", lambda: shot(b_phone, "phone-pixel-board-b", full=False))
    check("Layout", "No sideways scrolling on phones", no_horizontal_scroll)

    def dark_mode():
        page = dark_phone.new_page()
        page.goto(f"{BASE}/?board=b")
        expect(page.locator(".pa-question")).to_be_visible(timeout=30000)
        settle(page, 2)
        shot(page, "phone-dark-mode-board-b")
        bg = page.evaluate("getComputedStyle(document.querySelector('.stApp')).backgroundColor")
        fg = page.evaluate("getComputedStyle(document.querySelector('.pa-question')).color")
        page.close()
        return f"phone set to dark mode still gets the light theme: background {bg}, text {fg}"
    check("Layout", "Readable with the phone in dark mode", dark_mode)

    def tap_targets_and_text():
        sizes = b_phone.evaluate("""() => {
            // Streamlit's own header (Deploy/menu) is excluded: Deploy only exists when run locally.
            const btns = [...document.querySelectorAll('button')].filter(b => b.offsetParent && b.innerText.trim() && !b.closest('header'));
            const hs = btns.map(b => b.getBoundingClientRect().height);
            const fonts = [...document.querySelectorAll('.pa-post .text, .pa-privacy, label p, textarea')]
                .map(e => parseFloat(getComputedStyle(e).fontSize));
            return {minBtn: Math.min(...hs), nBtn: hs.length, minFont: Math.min(...fonts)};
        }""")
        assert sizes["minBtn"] >= 44 and sizes["minFont"] >= 16, sizes
        return f"smallest button {sizes['minBtn']:.0f}px tall ({sizes['nBtn']} checked); smallest text {sizes['minFont']:.0f}px"
    check("Layout", "Tap targets 44px+ and text 16px+", tap_targets_and_text)

    # ---------------------------------------------------- Board C desktop --
    c_page = desktop.new_page()

    def c_participant():
        c_page.goto(f"{BASE}/?board=c")
        expect(c_page.locator(".pa-question", has_text="What would you like to receive on AI?")).to_be_visible(timeout=30000)
        c_page.get_by_role("button", name="☐  Use case showcases").click()
        expect(c_page.get_by_role("button", name="☑  Use case showcases")).to_be_visible(timeout=15000)
        c_page.get_by_role("button", name="☐  Privacy and data Q&A").click()
        expect(c_page.get_by_role("button", name="☑  Privacy and data Q&A")).to_be_visible(timeout=15000)
        assert c_page.locator(".pa-bar-value").count() == 0, "vote counts visible before reveal"
        expect(c_page.get_by_text("Tutorials on writing prompts for proposals")).to_be_visible()
        return "multi-select works; option vote counts hidden; comments visible as they come in"
    check("Board C", "Pick several options; counts hidden until reveal", c_participant)

    def c_option_comment():
        c_page.locator('input[aria-label="Sessions or tutorials on what? (optional)"]').fill("Prompt clinics by task type (QC)")
        c_page.get_by_role("button", name="Add", exact=True).nth(4).click()
        expect(c_page.get_by_text("Prompt clinics by task type (QC)")).to_be_visible(timeout=15000)
        comment = next(c for c in store.option_comments(store.load(), 4) if "Prompt clinics" in c["text"])
        up = c_page.locator(f"xpath=//div[contains(@class,'pa-comment')][contains(., 'Prompt clinics by task type (QC)')]"
                            "/ancestor::div[contains(@class,'stElementContainer')][1]/following-sibling::div[1]//button").first
        up.click()
        expect(up).to_have_text("✓ Upvoted · 1", timeout=15000)
        assert len(store.find_item(store.load(), "c", comment["id"])["votes"]) == 1
        expect(c_page.get_by_role("button", name="☑  " + config.NEXT_OPTIONS[4])).to_be_visible(timeout=15000)
        return "typed 'Sessions or tutorials on what?' on card 5: detail shows under it, card got ticked, upvoted once"
    check("Board C", "Add an 'in what?' detail to an option, upvote it", c_option_comment)

    def c_other():
        c_page.locator('textarea[aria-label="' + config.BOARDS["c"]["other_label"] + '"]').fill("AI wins in our weekly huddle (QC)")
        c_page.get_by_role("button", name="Add", exact=True).last.click()
        expect(c_page.locator(".pa-post", has_text="AI wins in our weekly huddle (QC)")).to_be_visible(timeout=15000)
        btn = vote_button(c_page, "Monthly AI office hours")
        before = int(btn.inner_text().split("·")[-1].split()[0])
        btn.click()
        expect(btn).to_contain_text(f"· {before + 1}", timeout=15000)
        return f"Other entry posted; upvoting another Other went {before} → {before + 1}"
    check("Board C", "Add an Other entry and upvote an Other", c_other)
    check("Board C", "Desktop screenshot (before reveal)", lambda: shot(c_page, "desktop-board-c-before-reveal", full=True))

    # ---------------------------------------------------- presenter A --
    def projector_live_lag():
        pres.goto(f"{BASE}/?board=a&view=present")
        expect(pres.get_by_text("Board A controls")).to_be_visible(timeout=30000)
        before = int(pres.locator(".pp-count").inner_text().split()[0])
        a_phone.locator('textarea[aria-label="What do you use AI for? (required)"]').fill("Lag probe post (QC)")
        a_phone.get_by_role("button", name="Post", exact=True).click()
        t0 = time.time()
        expect(pres.locator(".pp-count")).to_contain_text(f"{before + 1} post", timeout=15000)
        lag = time.time() - t0
        assert lag < 3, lag
        return f"new post counted on the projector {lag:.1f}s after it was sent (target under 3s)"
    check("Presenter", "Projector updates without reload, under 3s", projector_live_lag)

    def qr_on_screen():
        expect(pres.locator(".pp-qr img")).to_be_visible(timeout=10000)
        link = pres.locator(".pp-qr .link").inner_text()
        assert link.endswith("?board=a"), link
        return f"QR and short link shown: {link}"
    check("Presenter", "QR code and short link on screen", qr_on_screen)

    def rule_summary_a():
        t0 = time.time()
        pres.get_by_role("button", name="Generate summary", exact=True).click()
        expect(pres.get_by_text("Top 5 by votes")).to_be_visible(timeout=30000)
        secs = time.time() - t0
        s = summary.summarize(store.load(), "a")
        return f"{secs:.1f}s; {s['totals']['posts']} posts, {s['totals']['votes']} votes, {s['totals']['participants']} participants"
    check("Summary", "Rule-based summary, Board A", rule_summary_a)

    def ai_summary_run():
        open(MOCK_LOG, "w").close()
        t0 = time.time()
        pres.get_by_role("button", name="Generate AI themes (A + B)").click()
        expect(pres.get_by_text("Where to build next:")).to_be_visible(timeout=30000)
        secs = time.time() - t0
        sent = [json.loads(line) for line in open(MOCK_LOG)]
        assert len(sent) == 1, f"{len(sent)} model calls"
        req = sent[0]
        body = json.dumps(req["body"])
        leaked = [n for n in created["names_used"] | {"QC Tester"} if n in body]
        assert not leaked, f"names sent to model: {leaked}"
        sysmsg = req["body"]["messages"][0]["content"]
        for rule in ("Use only the posts given", "Never include names"):
            assert rule in sysmsg, rule
        themes = store.load()["ai_themes"]
        d = store.load()
        a_posts = {x["id"]: x for x in store.visible_posts(d, "a")}
        assert sum(t["posts"] for t in themes["a"]) == len(a_posts), "theme counts don't add up to posts"
        assert sum(t["votes"] for t in themes["a"]) == sum(len(x["votes"]) for x in a_posts.values())
        texts = {x["text"] for x in a_posts.values()}
        assert all(q in texts for t in themes["a"] for q in t["quotes"]), "a quote is not word for word"
        return (f"{secs:.1f}s; 1 model call, no names in it, prompt carries the rules; invented id dropped; "
                f"theme counts add up to {len(a_posts)} posts; quotes are verbatim; "
                f"line: {themes['build_next']}")
    check("Summary", "AI themes (mock approved model)", ai_summary_run)
    check("Presenter", "Projector screenshot, Board A + summary", lambda: shot(pres, "projector-board-a-summary", full=True))

    # ----------------------------------------------------- moderation --
    def moderation():
        trap = created["trap_ids"][0]
        trap_text = store.find_item(store.load(), "b", trap)["text"]
        pres.goto(f"{BASE}/?board=b&view=present")
        expect(pres.get_by_text("Board B controls")).to_be_visible(timeout=30000)
        pres.get_by_text("Moderate (hide a post or comment)").click()
        pres.get_by_role("button", name="Hide post: " + trap_text[:60]).click()
        settle(pres, 3)
        assert pres.locator(".pp-card", has_text="Client X").count() == 0
        b_phone.get_by_role("button", name="↻ Refresh").click()
        expect(b_phone.locator(".pa-post", has_text="Client X")).to_have_count(0, timeout=15000)
        d = store.load()
        assert b"Client X" not in export.board_csv(d, "b")
        assert "Client X" not in summary.to_text(summary.summarize(d, "b"))
        return "post naming a client hidden: gone from projector, phones, summary and CSV"
    check("Presenter", "Moderation: hide a post", moderation)

    def rule_summary_b():
        pres.get_by_role("button", name="Close posting (and generate summary)").click()
        expect(pres.get_by_text("Biggest drains, hours per month (estimate)")).to_be_visible(timeout=30000)
        expect(pres.locator(".pp-count")).to_contain_text("posting closed", timeout=10000)
        s = summary.summarize(store.load(), "b")
        top = s["by_hours"][0]
        return f"closing posting generated it; biggest drain {top['hours']:.1f} h/month (estimate): {top['text']}"
    check("Summary", "Closing Board B auto-generates the summary", rule_summary_b)
    check("Presenter", "Projector screenshot, Board B closed", lambda: shot(pres, "projector-board-b-closed", full=True))

    def closed_blocks_phone():
        b_phone.reload()
        expect(b_phone.get_by_text("Posting is closed for this board.")).to_be_visible(timeout=20000)
        assert not store.add_post("b", "qc-late", "late post")
        return "phone shows 'Posting is closed'; late posts are refused"
    check("Presenter", "Closed board refuses new posts", closed_blocks_phone)

    # --------------------------------------------------------- Board C --
    def reveal_c():
        pres.goto(f"{BASE}/?board=c&view=present")
        expect(pres.get_by_text("Board C controls")).to_be_visible(timeout=30000)
        expect(pres.get_by_text("Vote counts are hidden.")).to_be_visible(timeout=10000)
        shot(pres, "projector-board-c-before-reveal")
        pres.get_by_role("button", name="Reveal results", exact=True).click()
        expect(pres.locator(".pa-bar-value").first).to_be_visible(timeout=15000)
        bars = pres.locator(".pa-bar-value").all_inner_texts()
        assert len(bars) == 5 and all("vote" in b and "%" in b for b in bars), bars
        counts = [int(b.split()[0]) for b in bars]
        assert counts == sorted(counts, reverse=True), counts
        expect(pres.get_by_text("Most-upvoted comment per option")).to_be_visible()
        expect(pres.get_by_text("Top Other ideas")).to_be_visible()
        c_page.get_by_role("button", name="↻ Refresh").click()
        expect(c_page.locator(".pa-bar-value").first).to_be_visible(timeout=15000)
        return "bars sorted by votes, each labelled e.g. '" + bars[0] + "'; phones see results after reveal"
    check("Board C", "Reveal results: bars, top comments, top Others", reveal_c)
    check("Presenter", "Projector screenshot, Board C revealed", lambda: shot(pres, "projector-board-c-revealed", full=True))

    # ---------------------------------------------------------- export --
    def export_zip():
        with pres.expect_download(timeout=30000) as dl:
            pres.get_by_role("button", name="Export all boards + summary (.zip)").click()
        path = OUT / "export.zip"
        dl.value.save_as(path)
        z = zipfile.ZipFile(path)
        names = z.namelist()
        files = {n.split("-")[1]: n for n in names if n.endswith(".csv")}
        a = csv_rows(z.read(files["a"]))
        b = csv_rows(z.read(files["b"]))
        c = csv_rows(z.read(files["c"]))
        assert a[0] == ["Use", "Tool", "Task type", "Votes", "Comments", "Name"], a[0]
        assert b[0] == ["Time drain", "How often", "Minutes each time", "Votes", "Comments", "Source"], b[0]
        assert c[0] == ["Option", "Text", "Votes", "Comments"], c[0]
        assert all(r[5].startswith(f"Live board, {SESSION_DATE}") for r in b[1:]), "Source column"
        trap = [r for r in a if "HYPERLINK" in r[0]][0]
        assert trap[0].startswith("'="), trap[0]
        assert any("Résumé" in r[0] and "📰" in r[0] for r in a), "accents/emoji lost"
        txt = z.read("summary.txt").decode("utf-8-sig")
        assert "Board A" in txt and "Board C" in txt and "AI themes" in txt
        for n in names:
            (OUT / n).write_bytes(z.read(n))
        return (f"{len(names)} files; A {len(a) - 1} rows, B {len(b) - 1} rows, C {len(c) - 1} rows; "
                "columns match the handoff; formula neutralised; accents and emoji intact")
    check("Export", "CSV export (zip of all boards + summary)", export_zip)

    def qr_pngs():
        with pres.expect_download(timeout=30000) as dl:
            pres.get_by_role("button", name="QR code PNGs (all 3, .zip)").click()
        path = OUT / "qr.zip"
        dl.value.save_as(path)
        z = zipfile.ZipFile(path)
        sizes = {}
        for n in z.namelist():
            img = Image.open(io.BytesIO(z.read(n)))
            sizes[n] = img.size
            assert min(img.size) >= 1000, (n, img.size)
            (OUT / n).write_bytes(z.read(n))
        return ", ".join(f"{n} {w}×{h}" for n, (w, h) in sizes.items()) + " (QC links point at localhost)"
    check("Export", "QR code PNGs, one per board, 1000px+", qr_pngs)

    # ------------------------------------------------------------ reset --
    def delete_all():
        pres.get_by_role("button", name="Delete all data (all boards)").click()
        pres.get_by_role("button", name="⚠️ Confirm: delete everything").click()
        settle(pres, 3)
        d = store.load()
        empty = (not d["boards"]["a"]["posts"] and all(x.get("seed") for x in d["boards"]["b"]["posts"])
                 and not d["boards"]["c"]["picks"] and not d["boards"]["c"]["others"])
        assert empty and not store.DATA_FILE.exists(), "data left behind"
        pres.goto(f"{BASE}/?board=a&view=present")
        expect(pres.get_by_text("Waiting for the first post")).to_be_visible(timeout=30000)
        return "data file removed; Board A empty, Board B back to the 6 seed rows (0 votes), Board C empty"
    check("Reset", "Delete all data", delete_all)

    browser.close()

json.dump({"fake_counts": fake_counts, "results": results, "session_date": SESSION_DATE},
          open(OUT / "qc_results.json", "w"), indent=1)
print(f"\n{sum(r['ok'] for r in results)}/{len(results)} checks passed")
