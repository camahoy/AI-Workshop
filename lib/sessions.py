"""Per-session settings, keyed by session code.

Every session stores its own `config` inside its board document, so each
session can show a different set of tabs, a different Join form, and a
different anonymity rule without code changes. A new session takes its
starting config from a template, chosen by the facilitator on the setup
screen (or forced by PRESETS for codes that must always behave a set way).
Sessions created before per-session config existed have no stored config
and fall back to the "workshop" template, so they behave exactly as before.

The facilitator can change tabs and the summary switch per session from
the sidebar at any time; those changes are saved with that session only.
"""

ALL_TABS = ["join", "notes", "map", "ideas", "ailog", "everyone", "closing"]

TEMPLATES = {
    "workshop": {
        "label": "Field Notes workshop (SF-01 style)",
        "tabs": ["join", "notes", "map", "ideas", "everyone", "closing"],
        # Join asks Service Line, Title, Level; posts carry a Service Line · Title tag.
        "anonymous": False,
        # "bottleneck" = Bottleneck Bank wording; "friction" = Friction Points wording.
        "ideas_style": "bottleneck",
        "summary_enabled": True,
        "summary_style": "workshop",
    },
    "pulse": {
        "label": "Team pulse (PA-01 style)",
        "tabs": ["join", "ideas", "ailog"],
        # Join asks Level only; Level is stored privately for the export and
        # never shown; no identity tag on any post.
        "anonymous": True,
        "ideas_style": "friction",
        "summary_enabled": False,
        "summary_style": "pulse",
    },
}

# Codes that always start from a given template, whatever the setup screen says.
PRESETS = {"SF-01": "workshop", "PA-01": "pulse"}

DEFAULT_TEMPLATE = "workshop"


def template_for_code(code: str, chosen: str | None = None) -> str:
    return PRESETS.get(code) or chosen or DEFAULT_TEMPLATE


def config_from_template(name: str) -> dict:
    t = TEMPLATES[name]
    return {
        "template": name,
        "tabs": list(t["tabs"]),
        "anonymous": t["anonymous"],
        "ideas_style": t["ideas_style"],
        "summary_enabled": t["summary_enabled"],
        "summary_style": t["summary_style"],
    }


def config_for(code: str, data: dict) -> dict:
    """Stored config merged over its template's defaults. A session with
    no stored config uses its preset template, else the workshop default."""
    stored = data.get("config") or {}
    base = config_from_template(stored.get("template") or template_for_code(code))
    base.update(stored)
    tabs = [t for t in ALL_TABS if t in base.get("tabs", [])]
    base["tabs"] = tabs or ["join"]
    return base


def tab_label(key: str, cfg: dict) -> str:
    if key == "ideas":
        return "Friction Points" if cfg["ideas_style"] == "friction" else "Bottleneck Bank"
    return {
        "join": "Join",
        "notes": "Good Research",
        "map": "Meaning & Delegation",
        "ailog": "AI in Our Work",
        "everyone": "N = Everyone",
        "closing": "Closing",
    }[key]


# ------------------------------------------------------------ AI in Our Work --
AI_TOOLS = [
    "Company-provided Copilot",
    "A personal AI account",
    "A tool built by my team",
    "A third-party research platform with AI features",
    "Other",
]
AI_OUTCOMES = ["Worked well", "Partly", "Didn't work"]
AI_BARRIERS = [
    "Unsure what data I can put in",
    "It can't reach the information it needs",
    "Output needs heavy rework",
    "Not sure how to prompt or where to start",
    "No time to learn or test it",
    "Our systems don't connect",
    "I don't trust the accuracy",
    "Other",
]
AI_TIME_IMPACT = ["Saved time", "About the same", "Lost time"]
