# `llm/` folder — Generative AI and LLMs (brief §5, 4 points)

| File | Role | Who fills it |
|---|---|---|
| `make_stats_summary.py` | Regenerates `stats_summary.md` from `results/` (`python llm/make_stats_summary.py`) | code |
| `stats_summary.md` | All the project's numbers, **without interpretation**: the only material given to the LLM | code |
| `prompts.md` | 4 ready-to-copy prompts (a: model hypotheses; b: plain-language explanation; c: simulated recommendations and limits; d: self-check) | — |
| `my_interpretation_TEMPLATE.md` | Expert interpretation, to write **before** consulting the LLM | **student** |
| `answers/` | Prompts sent and **full** LLM answers (report appendix) | **student** (copy) |
| `comparison_TEMPLATE.md` | Table: LLM statement / correct? / error type / correction / evidence | **student** |
| `CHECKLIST_LLM_ERRORS.md` | Typical errors to look for on this project, with the reference to check each one | — |
| `run_ollama.py` | Optional: sends prompts a–d to a **local** Ollama model (default `qwen2.5:3b`) following `prompts.md` exactly, and writes `answers/prompt_a..d.md` verbatim with model/version/date headers. Refuses to run before `my_interpretation.md` exists, and never overwrites answers without `--force` | code |

**Local run:** Ollama running (installed via `winget install Ollama.Ollama`; model via `ollama pull qwen2.5:3b`), then `.venv\Scripts\python.exe llm/run_ollama.py` (about 10–20 min on CPU). `--model` selects another pulled model.

**Order:**
1. `my_interpretation.md`;
2. prompts a, b, c in new conversations, then d;
3. `answers/`;
4. `comparison.md`;
5. LLM section of the report (Phase 9).

No LLM answer has been written or simulated in this folder.
