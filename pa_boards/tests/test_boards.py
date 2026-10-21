import csv
import io
import time
import zipfile
from concurrent.futures import ThreadPoolExecutor

from palib import ai_summary, config, export, qr, summary


def test_vote_once_per_browser_and_undo(store):
    p = store.add_post("a", "b1", "Drafting client emails", tool="Copilot")
    assert store.toggle_vote("a", p["id"], "b2") is True
    assert store.toggle_vote("a", p["id"], "b2") is False  # undo
    store.toggle_vote("a", p["id"], "b2")
    store.toggle_vote("a", p["id"], "b3")
    post = store.find_post(store.load(), "a", p["id"])
    assert sorted(post["votes"]) == ["b2", "b3"]


def test_sort_by_votes_then_newest(store):
    old = store.add_post("a", "b1", "old")
    time.sleep(0.01)
    new = store.add_post("a", "b1", "new")
    top = store.add_post("a", "b1", "top")
    store.toggle_vote("a", top["id"], "b9")
    order = [p["text"] for p in store.visible_posts(store.load(), "a")]
    assert order == ["top", "new", "old"]
    assert old and new


def test_validation_and_limits(store):
    assert store.add_post("a", "b1", "   ") is None
    p = store.add_post("a", "b1", "x" * 500, tool="Not a tool", task="Summary")
    assert len(p["text"]) == config.MAX_POST_CHARS
    assert p["tool"] == "" and p["task"] == "Summary"
    q = store.add_post("b", "b1", "tabs", freq="Weekly", minutes="abc")
    assert q["minutes"] is None and q["freq"] == "Weekly"


def test_closed_board_rejects_everything(store):
    p = store.add_post("b", "b1", "checking tables")
    store.set_board_flag("b", "open", False)
    assert store.add_post("b", "b1", "late") is None
    assert store.toggle_vote("b", p["id"], "b2") is None
    assert store.add_comment("b", p["id"], "b2", "hi") is False


def test_hide_removes_from_feed_and_export(store):
    p = store.add_post("a", "b1", "something inappropriate")
    store.set_hidden("a", p["id"], True)
    data = store.load()
    assert all(x["id"] != p["id"] for x in store.visible_posts(data, "a"))
    assert b"inappropriate" not in export.board_csv(data, "a")
    assert store.toggle_vote("a", p["id"], "b2") is None


def test_seed_switch(store):
    data = store.load()
    seeds = [p for p in data["boards"]["b"]["posts"] if p["seed"]]
    assert len(seeds) == len(config.SEEDS_B) and all(not p["votes"] for p in seeds)
    store.set_setting("seed_b", False)
    assert not store.load()["boards"]["b"]["posts"]
    store.set_setting("seed_b", True)
    store.set_setting("seed_b", True)  # idempotent
    assert len(store.load()["boards"]["b"]["posts"]) == len(config.SEEDS_B)


def test_reset_and_delete_all(store):
    store.add_post("a", "b1", "x")
    store.add_post("b", "b1", "y")
    store.toggle_pick("b1", 0)
    store.reset_board("a")
    data = store.load()
    assert data["boards"]["a"]["posts"] == []
    assert any(p["text"] == "y" for p in data["boards"]["b"]["posts"])
    store.delete_all()
    data = store.load()
    assert not store.DATA_FILE.exists()
    assert data["boards"]["c"]["picks"] == {}
    assert all(p["seed"] for p in data["boards"]["b"]["posts"])


def test_retention_purge(store):
    store.add_post("a", "b1", "x")
    store.set_setting("session_date", "2020-01-01")
    data = store.load()  # 30 days after 2020-01-01 is long past
    assert data["boards"]["a"]["posts"] == []
    assert not store.DATA_FILE.exists()


def test_hours_estimate(store):
    p = store.add_post("b", "b1", "tab checks", freq="Weekly", minutes=60)
    for b in ("b2", "b3"):
        store.toggle_vote("b", p["id"], b)
    post = store.find_post(store.load(), "b", p["id"])
    # 4.3 per month x 60 min / 60 x (2 upvoters + poster)
    assert abs(summary.hours_per_month(post) - 12.9) < 1e-9
    q = store.add_post("b", "b1", "no minutes", freq="Daily")
    assert summary.hours_per_month(store.find_post(store.load(), "b", q["id"])) is None


def test_summary_a_counts(store):
    store.set_setting("seed_b", False)
    store.add_post("a", "b1", "one", tool="Copilot", task="Summary")
    store.add_post("a", "b2", "two", tool="Copilot")
    p = store.add_post("a", "b3", "three", tool="Gemini", task="Summary")
    store.add_comment("a", p["id"], "b4", "nice")
    store.toggle_vote("a", p["id"], "b5")
    s = summary.summarize(store.load(), "a")
    assert s["totals"] == {"posts": 3, "seed_posts": 0, "votes": 1, "comments": 1, "participants": 5}
    assert dict(s["by_tool"]) == {"Copilot": 2, "Gemini": 1}
    assert dict(s["by_task"]) == {"Summary": 2, summary.NOT_GIVEN: 1}
    assert s["top"][0]["text"] == "three"
    assert "Top 5 by votes" in summary.to_text(s)


def test_board_c_multiselect_and_pct(store):
    store.toggle_pick("b1", 0)
    store.toggle_pick("b1", 3)
    store.toggle_pick("b2", 0)
    store.toggle_pick("b3", 4)
    store.toggle_pick("b3", 4)  # untick
    store.add_other("b3", "Office hours")
    s = summary.summarize(store.load(), "c")
    assert s["totals"]["participants"] == 3
    first = s["options"][0]
    assert first["label"] == config.NEXT_OPTIONS[0] and first["votes"] == 2
    assert round(first["pct"]) == 67
    assert [o["text"] for o in s["others"]] == ["Office hours"]


def test_board_c_comments_and_others(store):
    store.toggle_pick("b1", 2)
    assert store.add_comment("c", store.option_parent(4), "b2", "Tutorials on prompts for proposals", "Kim")
    assert store.add_comment("c", store.option_parent(4), "b3", "Short videos please")
    store.add_other("b4", "Monthly office hours")
    data = store.load()
    other = data["boards"]["c"]["others"][0]
    by_text = {c["text"]: c for c in store.option_comments(data, 4)}
    short, prompts = by_text["Short videos please"], by_text["Tutorials on prompts for proposals"]
    # comments and Others have their own upvotes; one per browser, undo works
    assert store.toggle_vote("c", prompts["id"], "b5") is True
    assert store.toggle_vote("c", prompts["id"], "b6") is True
    assert store.toggle_vote("c", prompts["id"], "b6") is False
    assert store.toggle_vote("c", other["id"], "b5") is True
    assert store.add_comment("c", other["id"], "b6", "Fridays work best")
    store.set_hidden("c", short["id"], True)
    s = summary.summarize(store.load(), "c")
    opt = next(o for o in s["options"] if o["label"] == config.NEXT_OPTIONS[4])
    assert opt["votes"] == 0 and opt["comments"] == [{"text": prompts["text"], "votes": 1}]
    assert s["others"] == [{"text": "Monthly office hours", "votes": 1,
                            "comments": [{"text": "Fridays work best", "votes": 0}]}]
    assert s["totals"]["participants"] == 6
    text = summary.to_text(s)
    assert "Short videos please" not in text and "Fridays work best" in text


def _rows(blob):
    assert blob.startswith(b"\xef\xbb\xbf")  # BOM so Excel reads UTF-8
    return list(csv.reader(io.StringIO(blob.decode("utf-8-sig"))))


def test_export_columns(store):
    store.set_setting("session_date", "2099-11-05")
    a = store.add_post("a", "b1", "=HYPERLINK(\"x\") summarising “threads”", tool="Copilot", task="Summary", name="Sam")
    store.add_comment("a", a["id"], "b2", "same here", "Jo")
    store.add_post("b", "b1", "Checking tabs, by hand", freq="Weekly", minutes=45)
    data = store.load()

    rows_a = _rows(export.board_csv(data, "a"))
    assert rows_a[0] == ["Use", "Tool", "Task type", "Votes", "Comments", "Name"]
    assert rows_a[1][0].startswith("'=")  # formula neutralised
    assert rows_a[1][4] == "same here (Jo)" and rows_a[1][5] == "Sam"

    rows_b = _rows(export.board_csv(data, "b"))
    assert rows_b[0] == ["Time drain", "How often", "Minutes each time", "Votes", "Comments", "Source"]
    live = [r for r in rows_b if r[0] == "Checking tabs, by hand"][0]
    assert live[1:4] == ["Weekly", "45", "0"] and live[5] == "Live board, 2099-11-05"
    assert sum("seed" in r[5] for r in rows_b[1:]) == len(config.SEEDS_B)

    store.add_other("b9", "Lunch-and-learn")
    store.add_comment("c", store.option_parent(0), "b9", "Two minutes each")
    data = store.load()
    rows_c = _rows(export.board_csv(data, "c"))
    assert rows_c[0] == ["Option", "Text", "Votes", "Comments"] and len(rows_c) == 7
    assert ["Other", "Lunch-and-learn", "0", ""] in rows_c
    assert [config.NEXT_OPTIONS[0], "", "0", "Two minutes each"] in rows_c

    z = zipfile.ZipFile(io.BytesIO(export.all_zip(data)))
    assert len(z.namelist()) == 4 and "summary.txt" in z.namelist()


def test_qr_png_size():
    from PIL import Image
    img = Image.open(io.BytesIO(qr.png(qr.participant_url("https://x.streamlit.app/", "b"))))
    assert img.size == (1200, 1200)
    assert qr.participant_url("https://x.streamlit.app/", "b") == "https://x.streamlit.app/?board=b"


def test_ai_assemble_guards(store):
    store.set_setting("seed_b", False)
    a1 = store.add_post("a", "b1", "Copilot drafts my emails", name="Pat")
    a2 = store.add_post("a", "b2", "Gemini for desk research")
    b1 = store.add_post("b", "b1", "Checking tables")
    b2 = store.add_post("b", "b2", "Formatting decks")
    store.toggle_vote("b", b1["id"], "b3")
    data = store.load()

    sent = ai_summary.build_input(data)
    assert "Pat" not in sent  # names never sent

    raw = {
        "board_a": [{"name": "Drafting", "post_ids": [a1["id"], "invented"], "representative_ids": [a1["id"]],
                     "matches_b_theme": "QA"}],
        "board_b": [{"name": "QA", "post_ids": [b1["id"], b1["id"]], "representative_ids": ["nope"]},
                    {"name": "Decks", "post_ids": [b2["id"]], "representative_ids": [b2["id"]]}],
    }
    t = ai_summary.assemble(data, raw)
    qa = next(x for x in t["b"] if x["name"] == "QA")
    assert qa["posts"] == 1 and qa["votes"] == 1 and qa["quotes"] == ["Checking tables"]
    unassigned = next(x for x in t["a"] if x["name"] == "Unassigned")
    assert unassigned["posts"] == 1 and unassigned["quotes"] == [a2["text"]]
    assert t["build_next"] == {"b_theme": "QA", "b_votes": 1, "a_theme": "Drafting"}
    assert "Where to build next: QA" in ai_summary.build_next_line(t)


def test_ai_off_without_secrets():
    assert ai_summary.provider_config({}) is None
    assert ai_summary.provider_config({"AI_SUMMARY_PROVIDER": "azure_openai"}) is None


def test_load_40_participants_concurrently(store):
    """40 simulated participants each post, vote on 10 posts and comment,
    all at once. Nothing is lost and a reader sees fresh state quickly."""
    store.set_setting("seed_b", False)
    seeds = [store.add_post("a", "seed", f"starter {i}")["id"] for i in range(10)]

    def participant(n):
        bid = f"sim{n}"
        store.add_post("a", bid, f"use {n}", tool="Copilot")
        for pid in seeds:
            store.toggle_vote("a", pid, bid)
        store.add_comment("a", seeds[n % 10], bid, f"comment {n}")
        store.toggle_pick(bid, n % 5)

    start = time.time()
    with ThreadPoolExecutor(max_workers=40) as pool:
        list(pool.map(participant, range(40)))
    elapsed = time.time() - start

    t0 = time.time()
    data = store.load()
    read_ms = (time.time() - t0) * 1000
    s = summary.summarize(data, "a")
    assert s["totals"]["posts"] == 50
    assert s["totals"]["votes"] == 400
    assert s["totals"]["comments"] == 40
    assert summary.summarize(data, "c")["totals"]["votes"] == 40
    assert elapsed < 10 and read_ms < 200, (elapsed, read_ms)


def test_summary_speed_100_posts(store):
    for i in range(100):
        p = store.add_post("b", f"x{i}", f"drain {i}", freq="Daily", minutes=10)
        store.toggle_vote("b", p["id"], f"y{i}")
    t0 = time.time()
    s = summary.summarize(store.load(), "b")
    summary.to_text(s)
    assert time.time() - t0 < 2
    assert len(s["top"]) == 5 and s["by_hours"][0]["hours"] == 21 * 10 / 60 * 2
