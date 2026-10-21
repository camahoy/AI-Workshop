"""Realistic fake entries for QC: ~30 people across the three boards.

Loaded through the same store functions the app uses, before the browser
part of the QC run. Includes deliberate traps: a post naming a client with
a figure (to moderate), a formula-looking post (Excel safety), accents and
emoji, and optional names (which must never reach the AI model).
"""
import random

from palib import config, store

NAMES = ["Priya", "Marcus", "Dana", "Luis", "Mei", "Tom", "Aisha", "Jonah"]

A_POSTS = [
    ("First drafts of client emails after a fieldwork delay", "Copilot", "Client email"),
    ("Rewriting deck headings so the storyline reads top-down", "Copilot", "Deck headings and storyline"),
    ("Summarising open-ends into a one-page readout", "Copilot", "Summary"),
    ("Checking toplines against banner tables before release", "Internal Ipsos tool", "Topline or tab check"),
    ("Tightening question wording in a tracker questionnaire", "Copilot", "Questionnaire design"),
    ("Background desk research on a new policy area", "Gemini", "Desk research"),
    ("Summarising meeting transcripts into action points", "Copilot", "Summary"),
    ("Drafting the methods section of a proposal", "Copilot", "Proposal"),
    ("Coding open-ended responses into first-pass themes", "Third-party research platform", "Qual analysis"),
    ("Writing Python to reshape weighting outputs", "Personal AI account", "Code or automation"),
    ("Checking crosstab significance flags look sensible", "Internal Ipsos tool", "Data analysis"),
    ("Polling methodology statement first drafts", "Copilot", "Polling documentation"),
    ("Turning long email threads into a status note", "Copilot", "Summary"),
    ("Screener wording checks for clarity", "Gemini", "Questionnaire design"),
    ("Formatting timesheet notes for iTime", "Copilot", "Admin"),
    ("Literature scan for a voter-turnout brief", "Gemini", "Desk research"),
    ("Excel formulas for a tab check workbook", "Copilot", "Code or automation"),
    ("Draft talking points for a client debrief", "Copilot", "Client email"),
    ("Résumé of press coverage on our latest poll 📰", "Gemini", "Desk research"),
    ("=HYPERLINK style formula pasted as text (Excel safety trap)", "Other", "Other"),
    ("Rewrite of a dense chart footnote", "", ""),
    ("Quick summary of a 40-page RFP", "Copilot", "Proposal"),
]

B_POSTS = [
    ("Filling in iTime and JobBook for the same job", "Weekly", 45),
    ("Checking survey links on every device before launch", "Weekly", 60),
    ("Re-checking data tables after each re-run", "Weekly", 90),
    ("Searching SharePoint and old decks for a past chart", "Weekly", 30),
    ("First drafts of RFP responses we rarely win", "Monthly", 240),
    ("Summarising long Teams threads I was copied on", "Daily", 15),
    ("Reformatting toplines into the client template", "Weekly", 40),
    ("Invoice and tracker updates across three spreadsheets", "Monthly", 120),
    ("Writing the same methods paragraph for every report", "Monthly", 30),
    ("Meeting notes into action lists", "Daily", 10),
    ("QA of translated questionnaires", "Quarterly", 180),
    ("Pulling past wording for trend questions", "Weekly", 20),
    ("Client X wants the 4.2m budget figure in the deck (moderation trap)", "", None),
    ("Building the same weekly status email", "Weekly", 25),
    ("Chasing approvals over email", "", None),
]

C_OPTION_COMMENTS = [
    (0, "Short demos from our own teams, not vendors"),
    (0, "Show real before/after time savings"),
    (4, "Tutorials on writing prompts for proposals"),
    (4, "Office hours we can drop into"),
    (3, "What we can and can't paste into Copilot"),
    (1, "Quarterly is enough"),
]

C_OTHERS = [
    "A shared prompt library for polling tasks",
    "Monthly AI office hours",
    "Examples of AI-checked tables that passed QA",
]


def load(seed: int = 7) -> dict:
    """Fills the store with a fake session. Returns what was created, for
    the QC checks to compare against."""
    rnd = random.Random(seed)
    people = [f"qc-person-{i:02d}" for i in range(30)]
    created = {"a": [], "b": [], "trap_ids": [], "names_used": set()}

    for i, (text, tool, task) in enumerate(A_POSTS):
        name = NAMES[i % len(NAMES)] if i % 3 == 0 else ""
        created["names_used"].add(name)
        p = store.add_post("a", people[i % 30], text, name, tool=tool, task=task)
        created["a"].append(p)
    for i, (text, freq, minutes) in enumerate(B_POSTS):
        name = NAMES[(i + 3) % len(NAMES)] if i % 4 == 0 else ""
        created["names_used"].add(name)
        p = store.add_post("b", people[(i + 5) % 30], text, name, freq=freq, minutes=minutes)
        created["b"].append(p)
        if "moderation trap" in text:
            created["trap_ids"].append(p["id"])

    data = store.load()
    for key in ("a", "b"):
        posts = data["boards"][key]["posts"]
        weights = [rnd.random() ** 2 for _ in posts]  # a few popular posts, a long tail
        for person in people:
            for post, w in zip(posts, weights):
                if rnd.random() < w * 0.6:
                    store.toggle_vote(key, post["id"], person)
        for post in rnd.sample(posts, 6):
            store.add_comment(key, post["id"], rnd.choice(people), "Same here, every week",
                              rnd.choice(["", "Mei"]))

    for person in people:
        picks = [i for i in range(len(config.NEXT_OPTIONS)) if rnd.random() < [0.7, 0.3, 0.35, 0.55, 0.65][i]]
        for i in picks:
            store.toggle_pick(person, i)
    for idx, text in C_OPTION_COMMENTS:
        store.add_comment("c", store.option_parent(idx), rnd.choice(people), text)
    for text in C_OTHERS:
        store.add_other(rnd.choice(people), text)
    data = store.load()
    for c in store.option_comments(data, 4):
        for person in rnd.sample(people, rnd.randint(2, 9)):
            store.toggle_vote("c", c["id"], person)
    for o in data["boards"]["c"]["others"]:
        for person in rnd.sample(people, rnd.randint(1, 8)):
            store.toggle_vote("c", o["id"], person)
    store.add_comment("c", data["boards"]["c"]["others"][0]["id"], people[3], "Yes, with examples by task type")
    created["names_used"].discard("")
    return created
