# Raw LLM answers

This folder is **empty on purpose**: the answers must come from a real LLM, queried by the student.

For each prompt in `llm/prompts.md`, create a file:

| File | Content |
|---|---|
| `prompt_a.md` | prompt a **exactly as sent** (pasted section included), then the full answer |
| `prompt_b.md` | same for prompt b |
| `prompt_c.md` | same for prompt c |
| `prompt_d.md` | follow-up d and the answer (state after which prompt it was sent) |

At the top of each file, write:

```
LLM: <name and exact version, e.g. "ChatGPT, GPT-x" or "Claude, model x">
Date and time: <YYYY-MM-DD HH:MM>
New conversation: yes / no
Conversation share link (if available): <url>
```

**Never** correct or shorten an answer: the LLM's errors are precisely what §5 of the brief asks you to analyse. Corrections go in `comparison.md`.

These files will be used as an appendix to the report (brief §5: "Document the prompt used and the answer obtained in full").
