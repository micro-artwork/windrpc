"""
gemini_review.py
Fetches the PR diff via GitHub API, sends it to Gemini for code review,
and posts the result as a PR comment.

Required environment variables:
  GEMINI_API_KEY  – Gemini API key (stored in GitHub Secrets)
  GITHUB_TOKEN    – Automatically provided by GitHub Actions
  PR_NUMBER       – Pull request number (set by workflow)
  REPO_FULL_NAME  – e.g. "micro-artwork/windrpc" (set by workflow)
  BASE_SHA        – Base commit SHA
  HEAD_SHA        – Head commit SHA
"""

import os
import sys
import json
import urllib.request
import urllib.error

# ── Environment ──────────────────────────────────────────────────────────────
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "").strip()
GITHUB_TOKEN   = os.environ.get("GITHUB_TOKEN", "").strip()
PR_NUMBER      = os.environ.get("PR_NUMBER", "")
REPO           = os.environ.get("REPO_FULL_NAME", "")   # owner/repo
BASE_SHA       = os.environ.get("BASE_SHA", "")
HEAD_SHA       = os.environ.get("HEAD_SHA", "")

# ── Early validation ─────────────────────────────────────────────────────────
if not GEMINI_API_KEY:
    print(
        "ERROR: GEMINI_API_KEY is not set or empty.\n"
        "  1. Get a key at https://aistudio.google.com/apikey\n"
        "  2. Add it as a GitHub Secret: Settings → Secrets → Actions → GEMINI_API_KEY",
        file=sys.stderr,
    )
    sys.exit(1)

if not GITHUB_TOKEN:
    print("ERROR: GITHUB_TOKEN is not available.", file=sys.stderr)
    sys.exit(1)

GEMINI_MODEL   = "gemini-2.5-flash"
MAX_DIFF_CHARS = 60_000   # Truncate very large diffs to stay within token limits

# Files to skip reviewing (generated, lock files, binary assets, etc.)
SKIP_EXTENSIONS = {
    ".pb.c", ".pb.h", ".pb.go", ".pb.js",
    ".options", ".lock", ".min.js", ".min.css",
    ".png", ".jpg", ".jpeg", ".gif", ".ico", ".svg",
    ".bin", ".hex", ".elf",
}
SKIP_PATHS = {"generated_flat/", "generated/", "build/", "dist/", "node_modules/"}


# ── GitHub API helpers ───────────────────────────────────────────────────────
def gh_request(method: str, path: str, body=None) -> dict | str:
    url = f"https://api.github.com/repos/{REPO}{path}"
    data = json.dumps(body).encode() if body else None
    req = urllib.request.Request(
        url,
        data=data,
        headers={
            "Authorization": f"Bearer {GITHUB_TOKEN}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
            "Content-Type": "application/json",
        },
        method=method,
    )
    with urllib.request.urlopen(req) as resp:
        return json.loads(resp.read())


def get_pr_diff() -> str:
    """Fetch the raw unified diff for the PR."""
    url = f"https://api.github.com/repos/{REPO}/pulls/{PR_NUMBER}"
    req = urllib.request.Request(
        url,
        headers={
            "Authorization": f"Bearer {GITHUB_TOKEN}",
            "Accept": "application/vnd.github.v3.diff",
            "X-GitHub-Api-Version": "2022-11-28",
        },
    )
    with urllib.request.urlopen(req) as resp:
        return resp.read().decode("utf-8", errors="replace")


def filter_diff(diff: str) -> str:
    """Remove generated/binary file sections from the diff."""
    lines = []
    skip = False
    for line in diff.splitlines(keepends=True):
        if line.startswith("diff --git"):
            skip = False
            filename = line.split(" b/")[-1].strip()
            if any(filename.endswith(ext) for ext in SKIP_EXTENSIONS):
                skip = True
            if any(p in filename for p in SKIP_PATHS):
                skip = True
        if not skip:
            lines.append(line)
    return "".join(lines)


def post_comment(body: str):
    """Post a comment on the PR."""
    gh_request("POST", f"/issues/{PR_NUMBER}/comments", {"body": body})


# ── Gemini API ───────────────────────────────────────────────────────────────
SYSTEM_PROMPT = """\
You are an expert code reviewer specializing in embedded systems, firmware (C/MCU), \
RPC frameworks, and multi-language SDKs (JavaScript, Python, C#).

The project is WindRPC — a zero-heap, static-memory RPC framework for microcontrollers \
using a 6-byte Little-Endian binary header + Protobuf payload over COBS or raw datagram transport.

Key rules to enforce during review:
- No dynamic memory allocation (malloc/calloc/free) in C callback handlers.
- Generated files (*.pb.c, *.pb.h, generated_flat/) must never be manually edited.
- Service IDs 1–6 are reserved; user services must use IDs 7–255.
- Always use proto3 syntax (not editions).
- Naming: snake_case for packages/services/rpcs/fields; PascalCase for messages/enums; UPPER_SNAKE_CASE for enum members.

Provide a structured review with the following sections:
1. **Summary** — One-paragraph overview of what this PR does.
2. **Issues** — List any bugs, correctness problems, or rule violations. Use severity tags: `[CRITICAL]`, `[HIGH]`, `[MEDIUM]`, `[LOW]`.
3. **Suggestions** — Optional improvements (performance, readability, style).
4. **Verdict** — One of: `✅ LGTM`, `⚠️ LGTM with minor suggestions`, or `❌ Changes requested`.

Be concise. Cite file paths and line numbers when possible.
"""


def call_gemini(diff: str) -> str:
    """Send diff to Gemini and return the review text."""
    if len(diff) > MAX_DIFF_CHARS:
        diff = diff[:MAX_DIFF_CHARS] + "\n\n[... diff truncated for length ...]"

    prompt = f"Please review the following pull request diff:\n\n```diff\n{diff}\n```"

    url = (
        f"https://generativelanguage.googleapis.com/v1beta/models/"
        f"{GEMINI_MODEL}:generateContent?key={GEMINI_API_KEY}"
    )
    payload = {
        "system_instruction": {"parts": [{"text": SYSTEM_PROMPT}]},
        "contents": [{"role": "user", "parts": [{"text": prompt}]}],
        "generationConfig": {
            "temperature": 0.2,
            "maxOutputTokens": 4096,
        },
    }
    data = json.dumps(payload).encode()
    req = urllib.request.Request(
        url,
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req) as resp:
            result = json.loads(resp.read())
            return result["candidates"][0]["content"]["parts"][0]["text"]
    except urllib.error.HTTPError as e:
        err = e.read().decode()
        print(f"Gemini API error {e.code}: {err}", file=sys.stderr)
        sys.exit(1)


# ── Main ─────────────────────────────────────────────────────────────────────
def main():
    print(f"Fetching diff for PR #{PR_NUMBER} in {REPO}...")
    raw_diff = get_pr_diff()
    filtered = filter_diff(raw_diff)

    if len(filtered.strip()) < 10:
        print("Diff is empty or only contains generated files. Skipping review.")
        post_comment(
            "🤖 **Gemini Code Review** — No reviewable changes detected "
            "(diff is empty or consists only of generated files)."
        )
        return

    print(f"Diff size: {len(filtered):,} chars. Calling Gemini ({GEMINI_MODEL})...")
    review = call_gemini(filtered)

    comment = (
        f"## 🤖 Gemini Code Review\n\n"
        f"> Model: `{GEMINI_MODEL}` &nbsp;|&nbsp; "
        f"Trigger: automated on PR &nbsp;|&nbsp; "
        f"[Re-run: comment `/gemini review`]\n\n"
        f"---\n\n"
        f"{review}\n\n"
        f"---\n"
        f"<sub>Generated by [gemini_review.py](.github/scripts/gemini_review.py). "
        f"Base: `{BASE_SHA[:7]}` → Head: `{HEAD_SHA[:7]}`</sub>"
    )

    print("Posting review comment to PR...")
    post_comment(comment)
    print("Done.")


if __name__ == "__main__":
    main()
