"""Stand-in for an Azure OpenAI chat/completions endpoint, for QC only.

    python pa_boards/tests/qc/mock_azure.py 8700 /path/to/requests.jsonl

It groups the post ids it receives into themes by keyword, the way a model
is asked to, and logs every request body so the QC run can check what the
app actually sends (e.g. that names never leave the app). It is NOT a model:
it tests the app's plumbing and guardrails, not the quality of real themes.
To exercise the guardrails it also invents one post id and repeats another.
"""
import json
import sys
from http.server import BaseHTTPRequestHandler, HTTPServer

PORT, LOG = int(sys.argv[1]), sys.argv[2]

THEMES_A = [
    ("Drafting emails and documents", ("email", "draft", "write", "rewrit", "proposal")),
    ("Summarising long material", ("summar", "notes", "transcript", "thread")),
    ("Checking data and tables", ("tab", "topline", "data", "check", "crosstab")),
    ("Research and background", ("research", "literature", "background", "desk", "news")),
    ("Questionnaire and wording", ("questionnaire", "question", "wording", "screener")),
]
THEMES_B = [
    ("Admin across systems", ("admin", "itime", "jobbook", "timesheet", "tracker", "invoice")),
    ("Finding past work", ("finding", "past", "portal", "sharepoint", "search")),
    ("Checking links and tables", ("test", "link", "table", "tab", "check", "qa")),
    ("Proposals and first drafts", ("proposal", "draft", "rfp", "bid")),
    ("Summarising threads", ("summar", "thread", "email", "teams", "meeting")),
]
MATCHES = {
    "Drafting emails and documents": "Proposals and first drafts",
    "Summarising long material": "Summarising threads",
    "Checking data and tables": "Checking links and tables",
}


def group(posts, themes, with_matches):
    out = {name: [] for name, _ in themes}
    other = []
    for p in posts:
        text = p["text"].lower()
        name = next((n for n, words in themes if any(w in text for w in words)), None)
        (out[name] if name else other).append(p["id"])
    result = []
    for name, ids in out.items():
        if ids:
            t = {"name": name, "post_ids": ids, "representative_ids": ids[:2]}
            if with_matches:
                t["matches_b_theme"] = MATCHES.get(name)
            result.append(t)
    if other:
        t = {"name": "Other uses", "post_ids": other, "representative_ids": other[:1]}
        if with_matches:
            t["matches_b_theme"] = None
        result.append(t)
    return result


class Handler(BaseHTTPRequestHandler):
    def do_POST(self):
        body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
        with open(LOG, "a") as f:
            f.write(json.dumps({"path": self.path, "api_key_present": bool(self.headers.get("api-key")),
                                "body": body}) + "\n")
        data = json.loads(body["messages"][1]["content"])
        a = group(data["board_a"], THEMES_A, True)
        b = group(data["board_b"], THEMES_B, False)
        if a:  # guardrail bait: an invented id and a duplicate
            a[0]["post_ids"] = a[0]["post_ids"] + ["p-invented-by-model", a[0]["post_ids"][0]]
        content = json.dumps({"board_a": a, "board_b": b})
        reply = json.dumps({"choices": [{"message": {"role": "assistant", "content": content}}]}).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(reply)))
        self.end_headers()
        self.wfile.write(reply)

    def log_message(self, *args):
        pass


HTTPServer(("127.0.0.1", PORT), Handler).serve_forever()
