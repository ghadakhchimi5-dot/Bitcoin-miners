"""Send the brief §5 prompts (llm/prompts.md) to a LOCAL Ollama model and save the answers verbatim.

Usage (from the project root, Ollama running):
    .venv\\Scripts\\python.exe llm/run_ollama.py                     # default model qwen2.5:3b
    .venv\\Scripts\\python.exe llm/run_ollama.py --model llama3.2:3b

What it does, following llm/prompts.md exactly:
  - prompt a, b, c each in a NEW conversation;
  - prompt d sent in the SAME conversation right after b, then again after c;
  - the [PASTE HERE ...] placeholder is replaced by the indicated sections of llm/stats_summary.md, copied as is;
  - writes llm/answers/prompt_a.md, prompt_b.md, prompt_c.md, prompt_d.md in the format of llm/answers/README.md,
    with the prompt exactly as sent and the FULL answer, never edited.

Guards: refuses to run before llm/my_interpretation.md exists (the expert interpretation must be written first),
and refuses to overwrite existing answer files (they are evidence) unless --force.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime
from pathlib import Path

import requests

ROOT = next(p for p in [Path(__file__).resolve().parent, *Path(__file__).resolve().parents] if (p / "config.yaml").exists())
LLM = ROOT / "llm"
ANSWERS = LLM / "answers"

# Which stats_summary.md sections each prompt receives (prompts.md, "[PASTE HERE ...]" lines).
SECTIONS = {"a": ["A"], "b": ["0", "B", "C"], "c": ["0", "C"]}
PLACEHOLDER = re.compile(r"\[PASTE HERE[^\]]*\]")


def load_prompts() -> dict[str, str]:
    text = (LLM / "prompts.md").read_text(encoding="utf-8")
    out = {}
    for m in re.finditer(r"^## Prompt ([a-d])\b.*?```\n(.*?)```", text, flags=re.S | re.M):
        out[m.group(1)] = m.group(2).rstrip("\n")
    missing = set("abcd") - out.keys()
    if missing:
        sys.exit(f"Could not find prompt(s) {sorted(missing)} in llm/prompts.md")
    return out


def load_sections() -> dict[str, str]:
    text = (LLM / "stats_summary.md").read_text(encoding="utf-8")
    parts = re.split(r"^(?=## )", text, flags=re.M)
    out = {}
    for p in parts:
        m = re.match(r"## ([0-9A-Z])\.", p)
        if m:
            out[m.group(1)] = p.rstrip("\n")
    return out


def fill(prompt: str, keys: list[str], sections: dict[str, str]) -> str:
    if not PLACEHOLDER.search(prompt):
        sys.exit("Placeholder [PASTE HERE ...] not found in a prompt")
    block = "\n\n".join(sections[k] for k in keys)
    return PLACEHOLDER.sub(lambda _: block, prompt, count=1)


class Ollama:
    def __init__(self, host: str, model: str, options: dict):
        self.host, self.model, self.options = host.rstrip("/"), model, options

    def info(self) -> dict:
        v = requests.get(f"{self.host}/api/version", timeout=10).json().get("version", "?")
        tags = requests.get(f"{self.host}/api/tags", timeout=10).json().get("models", [])
        tag = next((t for t in tags if t["name"] == self.model or t["model"] == self.model), None)
        if tag is None:
            sys.exit(f"Model {self.model} not pulled. Run: ollama pull {self.model}")
        d = tag.get("details", {})
        return {"ollama": v, "digest": tag.get("digest", "?")[:12], "params": d.get("parameter_size", "?"),
                "quant": d.get("quantization_level", "?"), "family": d.get("family", "?")}

    def chat(self, messages: list[dict]) -> tuple[str, dict]:
        r = requests.post(f"{self.host}/api/chat", stream=True, timeout=(10, 1800),
                          json={"model": self.model, "messages": messages, "stream": True, "options": self.options})
        r.raise_for_status()
        chunks, final = [], {}
        for line in r.iter_lines():
            if not line:
                continue
            j = json.loads(line)
            if "error" in j:
                sys.exit(f"Ollama error: {j['error']}")
            piece = j.get("message", {}).get("content", "")
            chunks.append(piece)
            print(piece, end="", flush=True)
            if j.get("done"):
                final = j
        print("\n")
        n_in, n_out = final.get("prompt_eval_count", 0), final.get("eval_count", 0)
        stats = {"prompt tokens": n_in, "answer tokens": n_out, "done_reason": final.get("done_reason", "?"),
                 "seconds": round(final.get("total_duration", 0) / 1e9, 1)}
        if n_in + n_out >= self.options["num_ctx"] - 16:
            print(f"WARNING: context window ({self.options['num_ctx']}) may have been exceeded — rerun with a larger --num-ctx")
        return "".join(chunks), stats


def header(info: dict, model: str, started: datetime, new_conv: str, options: dict) -> str:
    return (f"LLM: Ollama (local), model {model} — {info['family']}, {info['params']} parameters, {info['quant']}, "
            f"digest {info['digest']}; Ollama {info['ollama']}\n"
            f"Date and time: {started:%Y-%m-%d %H:%M}\n"
            f"New conversation: {new_conv}\n"
            f"Conversation share link (if available): none (local model, run by llm/run_ollama.py)\n"
            f"Generation options: {json.dumps(options)}\n")


def block(title: str, prompt: str, answer: str, stats: dict) -> str:
    return (f"\n## {title} — prompt exactly as sent\n\n````text\n{prompt}\n````\n\n"
            f"## {title} — full answer (verbatim, not edited)\n\n{answer}\n\n"
            f"*Run statistics: {json.dumps(stats)}*\n")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--model", default="qwen2.5:3b")
    ap.add_argument("--host", default="http://localhost:11434")
    ap.add_argument("--num-ctx", type=int, default=16384, help="context window; the default 2048 of Ollama would truncate the tables")
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--temperature", type=float, default=None, help="default: the model's own setting")
    ap.add_argument("--force", action="store_true", help="overwrite existing answer files")
    ap.add_argument("--skip-interpretation-check", action="store_true")
    a = ap.parse_args()

    if not a.skip_interpretation_check and not (LLM / "my_interpretation.md").exists():
        sys.exit("llm/my_interpretation.md not found. Write your expert interpretation BEFORE querying the LLM "
                 "(copy my_interpretation_TEMPLATE.md), then rerun.")
    outs = {k: ANSWERS / f"prompt_{k}.md" for k in "abcd"}
    existing = [p.name for p in outs.values() if p.exists()]
    if existing and not a.force:
        sys.exit(f"Answer files already exist: {existing}. They are evidence — use --force to overwrite.")

    options = {"num_ctx": a.num_ctx, "seed": a.seed}
    if a.temperature is not None:
        options["temperature"] = a.temperature
    llm = Ollama(a.host, a.model, options)
    try:
        info = llm.info()
    except requests.ConnectionError:
        sys.exit(f"Ollama is not reachable at {a.host}. Start it (Ollama app, or `ollama serve`).")

    prompts, sections = load_prompts(), load_sections()
    ANSWERS.mkdir(exist_ok=True)
    d_parts = []
    for k in "abc":
        started = datetime.now()
        print(f"=== Prompt {k} (new conversation) — {a.model} ===")
        sent = fill(prompts[k], SECTIONS[k], sections)
        conv = [{"role": "user", "content": sent}]
        answer, stats = llm.chat(conv)
        outs[k].write_text(header(info, a.model, started, "yes", options) + block(f"Prompt {k}", sent, answer, stats),
                           encoding="utf-8")
        if k in "bc":  # prompt d: same conversation, right after b (then after c)
            d_started = datetime.now()
            print(f"=== Prompt d (same conversation as prompt {k}) ===")
            conv += [{"role": "assistant", "content": answer}, {"role": "user", "content": prompts["d"]}]
            d_answer, d_stats = llm.chat(conv)
            d_parts.append(f"\n# Follow-up d sent after prompt {k} (same conversation)\n\n"
                           + header(info, a.model, d_started, f"no — continues the prompt {k} conversation (see prompt_{k}.md)", options)
                           + block(f"Prompt d (after {k})", prompts["d"], d_answer, d_stats))
            outs["d"].write_text("".join(d_parts).lstrip("\n"), encoding="utf-8")
    print("Saved:", ", ".join(str(p.relative_to(ROOT)) for p in outs.values()))


if __name__ == "__main__":
    main()
