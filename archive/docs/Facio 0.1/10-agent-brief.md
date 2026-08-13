# 10 — Agent brief

Checklist for implementing agents. Read [README](./README.md) + this file before coding.

---

## Source of truth

1. **`docs/Facio 0.1/`** — product decisions for UX, IA, terminology, scope  
2. **`apps/`** — current engine to extend  
3. **`docs/next/`** — how cycles/plugins/repair were built (reference, not override)  
4. **`docs/RFC/`** — long-horizon only; do not implement VectorDB/Coach marketplace in this wave  

If conflict: **Facio 0.1 wins** on product surface; keep next/RFC engine ideas when 0.1 says “preserve”.

---

## Before any PR, confirm

- [ ] Does this help Guide (*where?*) / Continue (*focus now?*) / Session (*execute how?*)?
- [ ] Can the user see a roadmap before Commitment?
- [ ] Is Home Continue with **Focus Engine** + **Hero Preview**, not a Guides inventory / `updated_at` dump?
- [ ] Is Guides drawer **compact nav** (not twin Cover cards of Continue)?
- [ ] Right Session presentation for the surface (Hero / Full / Compact)?
- [ ] Is AI still not the home screen?
- [ ] Are UI Blocks a closed client enum?
- [ ] Does daily Execute work without a new LLM call?
- [ ] Session = one opening + Session complete beat?
- [ ] Guide finite + Finish Experience on completion?
- [ ] Active AI apply = Diff + Undo; Create = Plan Feed cards + CTA on card ([15](./15-edit-surfaces.md))?
- [ ] Manual edits all UI Block tools on Create and Active?
- [ ] Micro-edits (skip/postpone) deterministic, not inside AI Feed?
- [ ] Cover / Identity on Guide surfaces (page / archive / thin drawer mark)?
- [ ] Did you avoid Instant Answer / chat-home / Accept-map duplicate / sticky bottom Start?
- [ ] Read [11](./11-success-systems.md) incl. §9 and [15](./15-edit-surfaces.md)?

---

## Preferred change style

- Reuse ProjectHome Session Stage → Session screen  
- Reuse Path data → Guide roadmap presentation  
- Reuse DraftStudio logic → **Plan Feed** Create Explore ([15](./15-edit-surfaces.md))  

- Reuse Projects list data → Continue cards + drawer  
- Prefer IA/navigation/copy changes before schema revolutions  
- Match existing RN/FastAPI patterns; no drive-by refactors  

---

## Anti-patterns (reject)

| Anti-pattern | Why |
|--------------|-----|
| Chat as home | Breaks positioning |
| Hide path until Start | Trust failure |
| Projects list as root | Wrong home question |
| Continue without Focus Engine | Accidental order = failed home |
| Booklet Session | Not executable |
| Multi-day lingering Session | Breaks atom |
| Silent Done / silent Guide completed | No story / no victory |
| Repair without Diff | Magic rewrite |
| Mutation without Undo | Fear of AI/edit |
| Infinite Guide default | No achievement |
| Open-ended LLM widgets | Client can’t render safely |
| Sonnet to fix grammar 400 | Wrong lever; see next/09 |
| Big-bang rename all `project` in one PR | High risk; alias later |
| “Just start” empty Guide | Violates P4 |

---

## Open product decisions (do not silently invent)

Escalate to human if blocking:

1. Exact Focus Engine weights / pin-Focus UX  
2. Incomplete Session policy (same-day resume window length)  
3. Streak definition on Identity  
4. Exact Morning Summary triggers/copy  
5. Final Cover + roadmap visual design system  
6. Whether Commitment is a separate route vs sticky CTA on Guide  
7. Instant Answer: hard delete vs hidden debug  
8. API rename timeline (`project` → `guide`)  
9. Session = exactly one schedule day vs multi-action day packaging  

Until decided: follow [05](./05-screens.md) / [06](./06-ux-flows.md) / [11](./11-success-systems.md) defaults.

---

## Suggested first implementation slice

1. Navigation: Continue root + Session + Guide + Create + drawer  
2. **Focus Engine v0** (deterministic sort + Focus card)  
3. Wire existing project/action/plugin data into new shells + Cover fields  
4. Commitment CTA on Guide; remove Instant Answer from happy path  
5. Session complete beat + Diff+Undo on Repair  
6. Swipe/≡ Session ↔ Guide  
7. Finish Experience on Guide complete  
8. Copy pass (Guide/Session/Continue/Start Guide)

Then: Identity polish, roadmap visuals, pencil edit hub, Morning Summary.

---

## Dogfood scenarios

Keep using:

- Cook carbonara (short Cycle, timeline)  
- Push-ups program (multi-day, stepper)  

Judge 0.1 by: trust before Start + daily Continue→Session loop — not by RFC completeness.
