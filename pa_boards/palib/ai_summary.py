"""Optional AI theme summary for Boards A and B. OFF by default.

It only runs when both are true:
  1. secrets set AI_SUMMARY_PROVIDER = "azure_openai" plus the endpoint,
     deployment and key of an Ipsos-approved Azure OpenAI deployment, and
  2. the presenter has switched "AI themes" on in the settings.

What the model sees: post id + post text (+ tool/task for A). Names are
never sent. The model only groups post ids into themes; theme counts and
vote totals are computed here, and the representative quotes are the
original post text looked up by id, so nothing is paraphrased.
"""
import json
import time

import requests

from palib import store

TIMEOUT_SECONDS = 25
DEFAULT_API_VERSION = "2024-10-21"

SYSTEM_PROMPT = """You group short workplace posts into themes.

Rules:
- Use only the posts given. Do not add facts, examples or posts of your own.
- Never include names of people, clients or companies in theme names.
- Theme names are short (2 to 6 words) and plain.
- For each board, make 3 to 6 themes. Put every post id in exactly one theme.
- For each theme, pick 1 or 2 representative post ids from that theme.
- For each Board A theme, set "matches_b_theme" to the name of the Board B theme it most clearly matches, or null if none clearly matches.

Return JSON only, in this shape:
{"board_a": [{"name": "...", "post_ids": ["..."], "representative_ids": ["..."], "matches_b_theme": "..." }],
 "board_b": [{"name": "...", "post_ids": ["..."], "representative_ids": ["..."]}]}"""


def provider_config(secrets) -> dict | None:
    """Returns the Azure OpenAI settings if fully configured, else None."""
    if str(secrets.get("AI_SUMMARY_PROVIDER", "")).lower() != "azure_openai":
        return None
    cfg = {
        "endpoint": secrets.get("AZURE_OPENAI_ENDPOINT", ""),
        "deployment": secrets.get("AZURE_OPENAI_DEPLOYMENT", ""),
        "api_key": secrets.get("AZURE_OPENAI_API_KEY", ""),
        "api_version": secrets.get("AZURE_OPENAI_API_VERSION", DEFAULT_API_VERSION),
    }
    return cfg if all(cfg.values()) else None


def build_input(data: dict) -> str:
    def rows(key):
        out = []
        for p in store.visible_posts(data, key):
            row = {"id": p["id"], "text": p["text"]}
            if key == "a":
                row.update({"tool": p.get("tool") or None, "task": p.get("task") or None})
            out.append(row)
        return out
    return json.dumps({"board_a": rows("a"), "board_b": rows("b")}, ensure_ascii=False)


def call_model(cfg: dict, user_content: str) -> dict:
    url = (
        f"{cfg['endpoint'].rstrip('/')}/openai/deployments/{cfg['deployment']}"
        f"/chat/completions?api-version={cfg['api_version']}"
    )
    resp = requests.post(
        url,
        headers={"api-key": cfg["api_key"], "Content-Type": "application/json"},
        json={
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_content},
            ],
            "temperature": 0,
            "response_format": {"type": "json_object"},
        },
        timeout=TIMEOUT_SECONDS,
    )
    resp.raise_for_status()
    return json.loads(resp.json()["choices"][0]["message"]["content"])


def assemble(data: dict, raw: dict) -> dict:
    """Turns the model's id groupings into themes with counts computed
    here and verbatim quotes. Ids the model invents are dropped; posts it
    leaves out go into an "Unassigned" theme so totals always add up."""
    result = {"generated_at": time.time(), "kind": "AI themes"}
    for key in ("a", "b"):
        posts = {p["id"]: p for p in store.visible_posts(data, key)}
        seen = set()
        themes = []
        for t in raw.get(f"board_{key}") or []:
            ids = [i for i in dict.fromkeys(t.get("post_ids", [])) if i in posts and i not in seen]
            if not ids:
                continue
            seen.update(ids)
            reps = [i for i in t.get("representative_ids", []) if i in ids][:2] or ids[:1]
            themes.append({
                "name": str(t.get("name") or "Untitled theme")[:60],
                "posts": len(ids),
                "votes": sum(len(posts[i]["votes"]) for i in ids),
                "quotes": [posts[i]["text"] for i in reps],
                "matches_b_theme": t.get("matches_b_theme") if key == "a" else None,
            })
        leftover = [i for i in posts if i not in seen]
        if leftover:
            themes.append({
                "name": "Unassigned",
                "posts": len(leftover),
                "votes": sum(len(posts[i]["votes"]) for i in leftover),
                "quotes": [posts[leftover[0]]["text"]],
                "matches_b_theme": None,
            })
        themes.sort(key=lambda t: (-t["votes"], -t["posts"]))
        result[key] = themes

    named_b = [t for t in result["b"] if t["name"] != "Unassigned"]
    top_b = named_b[0] if named_b else None
    match_a = None
    if top_b:
        match_a = next((t for t in result["a"] if t.get("matches_b_theme") == top_b["name"]), None)
    result["build_next"] = {
        "b_theme": top_b["name"] if top_b else None,
        "b_votes": top_b["votes"] if top_b else 0,
        "a_theme": match_a["name"] if match_a else None,
    }
    return result


def generate(data: dict, cfg: dict) -> dict:
    return assemble(data, call_model(cfg, build_input(data)))


def build_next_line(themes: dict) -> str:
    bn = themes["build_next"]
    if not bn["b_theme"]:
        return "Where to build next: not enough Board B posts yet."
    line = f"Where to build next: {bn['b_theme']} (Board B, {bn['b_votes']} votes)"
    if bn["a_theme"]:
        line += f", building on what already works in {bn['a_theme']} (Board A)"
    return line + "."


def to_text(themes: dict) -> str:
    when = time.strftime("%Y-%m-%d %H:%M", time.localtime(themes["generated_at"]))
    lines = [f"AI themes, Boards A and B (generated {when}; counts calculated in code)", ""]
    for key, title in (("a", "Board A: How we use AI"), ("b", "Board B: Time drains")):
        lines.append(title)
        for t in themes[key]:
            lines.append(f"- {t['name']}: {t['posts']} posts, {t['votes']} votes")
            lines += [f'    "{q}"' for q in t["quotes"]]
        lines.append("")
    lines.append(build_next_line(themes))
    return "\n".join(lines)
