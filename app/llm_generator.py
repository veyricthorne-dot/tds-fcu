import os
import base64
from pathlib import Path
from datetime import datetime
from dotenv import load_dotenv
import httpx

load_dotenv()
AIPIPE_TOKEN = os.getenv("AIPIPE_TOKEN")

TMP_DIR = Path("/tmp/llm_attachments")
TMP_DIR.mkdir(parents=True, exist_ok=True)

# --- attachment helpers remain the same ---
def decode_attachments(attachments):
    saved = []
    for att in attachments or []:
        name = att.get("name") or "attachment"
        url = att.get("url", "")
        if not url.startswith("data:"):
            continue
        try:
            header, b64data = url.split(",", 1)
            mime = header.split(";")[0].replace("data:", "")
            data = base64.b64decode(b64data)
            path = TMP_DIR / name
            with open(path, "wb") as f:
                f.write(data)
            saved.append({
                "name": name,
                "path": str(path),
                "mime": mime,
                "size": len(data)
            })
        except Exception as e:
            print("Failed to decode attachment", name, e)
    return saved

def summarize_attachment_meta(saved):
    summaries = []
    for s in saved:
        nm = s["name"]
        p = s["path"]
        mime = s.get("mime", "")
        try:
            if mime.startswith("text") or nm.endswith((".md", ".txt", ".json", ".csv")):
                with open(p, "r", encoding="utf-8", errors="ignore") as f:
                    if nm.endswith(".csv"):
                        lines = [next(f).strip() for _ in range(3)]
                        preview = "\\n".join(lines)
                    else:
                        data = f.read(1000)
                        preview = data.replace("\n", "\\n")[:1000]
                summaries.append(f"- {nm} ({mime}): preview: {preview}")
            else:
                summaries.append(f"- {nm} ({mime}): {s['size']} bytes")
        except Exception as e:
            summaries.append(f"- {nm} ({mime}): (could not read preview: {e})")
    return "\\n".join(summaries)

def _strip_code_block(text: str) -> str:
    if "```" in text:
        parts = text.split("```")
        if len(parts) >= 2:
            return parts[1].strip()
    return text.strip()

def generate_readme_fallback(brief: str, checks=None, attachments_meta=None, round_num=1):
    checks_text = "\\n".join(checks or [])
    att_text = attachments_meta or ""
    return f"""# Auto-generated README (Round {round_num})

**Project brief:** {brief}

**Attachments:**
{att_text}

**Checks to meet:**
{checks_text}

## Setup
1. Open `index.html` in a browser.
2. No build steps required.

## Notes
This README was generated as a fallback (AI Pipe did not return an explicit README).
"""

# --- new AI Pipe-based code generation ---
def generate_app_code(brief: str, attachments=None, checks=None, round_num=1, prev_readme=None):
    saved = decode_attachments(attachments or [])
    attachments_meta = summarize_attachment_meta(saved)

    context_note = ""
    if round_num == 2 and prev_readme:
        context_note = f"\n### Previous README.md:\n{prev_readme}\n\nRevise and enhance this project according to the new brief below.\n"

    user_prompt = f"""
You are a professional web developer assistant.

### Round
{round_num}

### Task
{brief}

{context_note}

### Attachments (if any)
{attachments_meta}

### Evaluation checks
{checks or []}

### Output format rules:
1. Produce a complete web app (HTML/JS/CSS inline if needed) satisfying the brief.
2. Output must contain **two parts only**:
   - index.html (main code)
   - README.md (starts after a line containing exactly: ---README.md---)
3. README.md must include:
   - Overview
   - Setup
   - Usage
   - If Round 2, describe improvements made from previous version.
4. Do not include any commentary outside code or README.
"""

    try:
        headers = {
            "Authorization": f"Bearer {AIPIPE_TOKEN}",
            "Content-Type": "application/json"
        }
        payload = {
            "model": "openai/gpt-4.1-nano",
            "messages": [
                {"role": "system", "content": "You are a helpful coding assistant that outputs runnable web apps."},
                {"role": "user", "content": user_prompt}
            ],
            "temperature": 0.7,
            "max_tokens": 3000
        }
        r = httpx.post("https://aipipe.org/openrouter/v1/chat/completions", headers=headers, json=payload, timeout=120)
        r.raise_for_status()
        resp_json = r.json()
        text = resp_json.get("choices", [{}])[0].get("message", {}).get("content", "")
        print("✅ Generated code using AI Pipe OpenRouter API.")
    except Exception as e:
        print("⚠ AI Pipe API failed, using fallback HTML instead:", e)
        text = f"""
<html>
  <head><title>Fallback App</title></head>
  <body>
    <h1>Hello (fallback)</h1>
    <p>This app was generated as a fallback because AI Pipe failed. Brief: {brief}</p>
  </body>
</html>

---README.md---
{generate_readme_fallback(brief, checks, attachments_meta, round_num)}
"""

    if "---README.md---" in text:
        code_part, readme_part = text.split("---README.md---", 1)
        code_part = _strip_code_block(code_part)
        readme_part = _strip_code_block(readme_part)
    else:
        code_part = _strip_code_block(text)
        readme_part = generate_readme_fallback(brief, checks, attachments_meta, round_num)

    files = {"index.html": code_part, "README.md": readme_part}
    return {"files": files, "attachments": saved}
