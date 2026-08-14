# 05 — AI and memory

## Role of AI

The assistant sits on the other side of the desk. Internally it **reads and writes desk objects through tools** (MCP or equivalent). The user never hears “MCP.”

They hear a short confirmation, or an explanation. They see the live tile change when schema changes. In chat, a bound widget appears as a **centered** snapshot (shared table).

A **lid-composer open** resumes the **current chat**. **New chat** (top of sheet) starts empty.

```text
User utterance (current chat, unless New chat)
  → (policy)
  → model with tools
  → tool: list_desk / get_widget / memory
  → maybe: create | update | complete | postpone | remind | remember
  → if mutated: live tile + centered snapshot in **this chat**
  → if explain-only: text, no new card
```

## When LLM is allowed

| Allowed | Examples |
|---------|----------|
| Place widgets from intent | “I want carbonara tonight” |
| Edit via talk | “add garlic”, “three sets not four”, “mark shopping done” |
| Explain the focused widget | “what is brisket?”, “what does chiffonade mean?” |
| Clarify if it branches the widgets | “how many people?” once |
| Morning question | one short operational line on a stalled object |
| Extract a MemoryFact | remark / explicit “remember” / visible “I’ll remember: more salt” |
| Rare messy repair | “I got sick, rebuild this week” |

Explain-only is success. Do not require a plan patch after a definition. An optional, dismissible “swap brisket for bacon?” is allowed; a forced next mutation is not.

## When LLM is forbidden

| Forbidden | Do this instead |
|-----------|-----------------|
| Render today-desk | persisted widgets |
| Tick, timer, stepper runtime | client (desk / fullscreen) |
| Run those runtimes inside a chat snapshot | snapshot is a picture |
| Fire reminder | scheduler |
| Rank “what’s on today” | P10 rules |
| Daily pep with no object | don’t send |
| Freeform new widget types | product ships a type |
| New snapshot card on a finger tick | only structural / commanded changes |
| Open-ended chat with no desk object | out of product |

## Tools (conceptual)

- `list_desk`, `get_widget`
- `create_widget`, `update_widget`, `archive_widget`
- `complete`, `skip`, `postpone`, `move_to_date`
- `set_reminder`
- `list_facts`, `remember`

Patches must validate against schema. Unvalidated model text never becomes widget payload.

## Context the model sees

**The desk, the focused widget, and relevant facts** — not the entire life transcript.

Current thread, truncated. Old threads opened explicitly. Do not concatenate all chats as “memory.”

## Memory

v1 = **MemoryFact** ([04](./04-domain-model.md)).

Write: check-in remark, explicit “remember”, visible extract after a play.  
Read: next placement of that `subject`; shown in talk or on the new tiles (“last time: more salt”).

Product metric: **hit rate** (applied + shown), not facts stored. One used fact beats forty unused. “It knows me” is a weeks-long accumulation of *hits* (constraints on the desk, defaults, outcomes, corrections) — not day-0 friendship.

**Not v1:** embedding the full chat as memory. Later retrieval over *facts and notes* is allowed; raw PII dumps and cross-user corpora are not ([06](./06-never-do.md)).

## Cost

- Finger path: ~0 tokens.
- Talk: one turn + tools, bounded. Explain-only still costs; keep answers short (a few sentences, tied to the step).
- Morning: generate only the optional one question, and only if showing a card.
- Inactive users: do not pep-push; wait until open.
- No hidden always-on coach loop.

## Voice (later)

Same tools, different mouth. After desk + chat work.

## Relationship to the old AI strategy

Keep: deterministic core, generative edge, no LLM on daily execute, validate patches, budget.

Drop as the center: blueprint compiler, 100k intents, Coach billing, Plan Feed as create UX, “every turn must PATCH.”

Create is: current chat → tools → tiles on the lid. Explain is: text beside a snapshot that did not need a new version. **New chat** is explicit. Kebab jumps to a chat, it does not replace New chat.
