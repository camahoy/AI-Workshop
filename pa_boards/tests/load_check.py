"""Load check against a running app (not part of pytest).

    python pa_boards/tests/load_check.py http://localhost:8600 test-pass [N]

Opens N (default 40) real browser sessions on Board B, staggered about a
second apart (like a room scanning a QR code). Once every page is loaded
they all post at the same moment, then each votes on several posts. Meanwhile a presenter session is
open, and the check measures how long after each marker post the
presenter screen shows it.
"""
import asyncio
import os
import sys
import time

from playwright.async_api import async_playwright

sys.path.insert(0, str(__import__("pathlib").Path(__file__).resolve().parent.parent))
from palib.config import SEEDS_B as SEEDS  # noqa: E402

BASE, PASS = sys.argv[1], sys.argv[2]
N = int(sys.argv[3]) if len(sys.argv) > 3 else 40


async def participant(ctx, n, results, loaded, go):
    await asyncio.sleep(n * 1.0)
    page = await ctx.new_page()
    await page.goto(f"{BASE}/?board=b")
    await page.wait_for_selector("textarea", timeout=120000)
    loaded.append(n)
    await go.wait()
    await page.locator("textarea").first.fill(f"Load test drain number {n}")
    await page.get_by_role("button", name="Post", exact=True).click()
    await page.wait_for_selector(f"text=Load test drain number {n}", timeout=60000)
    # Vote for three specific seed rows and wait to see each one confirmed
    # (✓) before the next, so we know exactly how many votes should exist.
    voted = 0
    for k in range(3):
        seed = SEEDS[(n + k) % len(SEEDS)]
        button = page.locator(
            f"xpath=//div[contains(@class,'pa-post')][div[@class='text' and text()={seed!r}]]"
            "/ancestor::div[contains(@class,'stElementContainer')][1]/following-sibling::div[1]//button"
        ).first
        # Seed rows have 0 votes and are oldest, so once there are more
        # than 15 posts they sit below the fold behind "Show all".
        deadline = time.time() + 30
        while not await button.count():
            show_all = page.get_by_role("button", name="Show all")
            if not await show_all.count():
                refresh = page.get_by_role("button", name="↻ Refresh")
                try:
                    await refresh.click(timeout=5000)  # phones don't redraw on a timer
                    await asyncio.sleep(3)
                except Exception:
                    pass
            if await show_all.count():
                try:
                    await show_all.first.click(timeout=5000)
                except Exception:
                    pass  # re-rendered under the click; try again

            if time.time() > deadline:
                raise TimeoutError(f"row {seed!r} never appeared")
            await asyncio.sleep(0.5)
        # Click, then wait for ✓. If the feed re-rendered under the click
        # (button swapped out), click again, as a person would.
        deadline = time.time() + 90
        while True:
            try:
                if (await button.inner_text(timeout=5000)).startswith("✓"):
                    break
                await button.click(timeout=5000)
                await asyncio.sleep(15)
            except Exception:
                pass
            if time.time() > deadline:
                raise TimeoutError(f"vote on {seed!r} never confirmed")
        voted += 1
    results.append(voted)


async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(executable_path=os.environ.get("CHROMIUM_PATH") or None)
        pres = await (await browser.new_context(viewport={"width": 1920, "height": 1080})).new_page()
        await pres.goto(f"{BASE}/?board=b&view=present")
        await pres.locator("input[type=password]").fill(PASS)
        await pres.get_by_role("button", name="Unlock").click()
        await pres.wait_for_selector("text=Board B controls", timeout=90000)

        marker = await (await browser.new_context()).new_page()
        await marker.goto(f"{BASE}/?board=b")
        await marker.wait_for_selector("textarea", timeout=60000)

        results, loaded, go = [], [], asyncio.Event()
        ctxs = [await browser.new_context(viewport={"width": 390, "height": 844}) for _ in range(N)]
        tasks = [asyncio.create_task(participant(c, i, results, loaded, go)) for i, c in enumerate(ctxs)]
        while len(loaded) < N and not all(t.done() for t in tasks):
            await asyncio.sleep(0.5)
        print(f"{len(loaded)}/{N} pages loaded; all post and vote now")
        t0 = time.time()
        go.set()

        # While the crowd is busy, post markers from a separate browser and
        # time how long until the projector shows each one.
        lags = []
        for i in range(3):
            await asyncio.sleep(3)
            text = f"Marker post {i}"
            await marker.locator("textarea").first.fill(text)
            await marker.get_by_role("button", name="Post", exact=True).click()
            await marker.wait_for_selector(f".pa-post:has-text('{text}')", timeout=60000)
            sent = time.time()
            # The projector shows only the top 12 cards, so compare the
            # live post count instead: wait until it has caught up with
            # the count the marker's own page saw right after posting.
            status = await marker.locator(".pa-status").first.inner_text()
            target = int(status.split()[0]) - 6  # minus the 6 seed rows
            await pres.wait_for_function(
                "t => { const m = document.body.innerText.match(/(\\d+) posts? ·/); return m && +m[1] >= t; }",
                arg=target, timeout=60000, polling=100)
            lags.append(time.time() - sent)
        done = await asyncio.gather(*tasks, return_exceptions=True)
        failures = [r for r in done if isinstance(r, Exception)]
        print(f"{len(results)}/{N} participants finished in {time.time() - t0:.1f}s, "
              f"{sum(results)} votes confirmed on screen; {len(failures)} failed: "
              f"{sorted({type(e).__name__ for e in failures})}")
        print("presenter lag per marker (s):", [round(x, 2) for x in lags])
        await browser.close()


asyncio.run(main())
