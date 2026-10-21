"""Fixed board definitions for the US Public Affairs AI session.

Everything participant-facing that's worded by the handoff lives here, so
a wording change never means hunting through UI code.
"""

BOARD_KEYS = ("a", "b", "c")

BOARDS = {
    "a": {
        "letter": "A",
        "name": "How we use AI",
        "question": "How do you use AI today?",
        "text_label": "What do you use AI for?",
        "vote_label": "I do this too",
    },
    "b": {
        "letter": "B",
        "name": "Time drains",
        "question": "Where does your time go that you'd hand to AI?",
        "text_label": "What would you hand to AI?",
        "vote_label": "Me too",
    },
    "c": {
        "letter": "C",
        "name": "What's next",
        "question": "What would you like to receive on AI?",
        "vote_label": "I'd like this too",
        "other_label": "Other: tell us what you'd like to receive",
    },
}

TOOLS = [
    "Copilot",
    "Gemini",
    "Personal AI account",
    "Third-party research platform",
    "Internal Ipsos tool",
    "Other",
]

TASK_TYPES = [
    "Client email",
    "Deck headings and storyline",
    "Summary",
    "Topline or tab check",
    "Questionnaire design",
    "Proposal",
    "Desk research",
    "Qual analysis",
    "Data analysis",
    "Polling documentation",
    "Admin",
    "Code or automation",
    "Other",
]

# Occurrences per month, used for the Board B hours estimate.
FREQUENCIES = {
    "Daily": 21,
    "Weekly": 4.3,
    "Monthly": 1,
    "Quarterly": 1 / 3,
}

NEXT_OPTIONS = [
    "Use case showcases",
    "Updates from senior leaders",
    "Newsletter of US Public Affairs wins",
    "Privacy and data Q&A",
    "Ask-me sessions and tutorials (e.g. building good prompts)",
]

# Board C: each option card has its own "in what?" input. Same order as NEXT_OPTIONS.
OPTION_PROMPTS = [
    ("Showcases of what?", "e.g. AI for tab checks, or drafting proposals"),
    ("Updates on what?", "e.g. which tools we're allowed to use"),
    ("Which wins should it cover?", "e.g. time saved on trackers"),
    ("What do you want answered?", "e.g. can I paste open-ends into Copilot?"),
    ("Sessions or tutorials on what?", "e.g. prompts for questionnaire design"),
]
assert len(OPTION_PROMPTS) == len(NEXT_OPTIONS)

SEED_LABEL = "From the 13 Aug session (other service lines)"
SEEDS_B = [
    "Admin spread across many sheets and systems (iTime, JobBook, trackers)",
    "Finding past research, slides and data across portals (Intranet, DeepSights, SharePoint)",
    "Summarising long email and Teams threads",
    "First drafts of technical proposals with low win probability",
    "Client and prospect info kept in several spreadsheets",
    "Testing survey links and checking data tables",
]

PRIVACY_LINE = "Describe the task, not the client. No client names, people's names or confidential figures."

MAX_POST_CHARS = 200
MAX_COMMENT_CHARS = 200
MAX_NAME_CHARS = 40
DEFAULT_RETENTION_DAYS = 30
