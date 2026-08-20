# Facio

Product: [`docs/rfc/`](docs/rfc/README.md)  
Engineering: [`docs/state/`](docs/state/README.md)  
Law: [`packages/domain/`](packages/domain/README.md)

**Roles.** PO = the human. Lead agent = PM (lid, theme, talk, contracts, review). Subagents = developers on a bounded slice **after** a contract exists.

Before code, read `docs/state/README.md` and the matching skill:

- `.cursor/skills/facio-product/SKILL.md` — always
- `.cursor/skills/facio-swiftui/SKILL.md` — `apps/mobile-swiftui` (plus SwiftUI expert skill in Task prompts)
- `.cursor/skills/facio-api/SKILL.md` — `apps/api` (plus `fastapi` and `pytest-patterns` in Task prompts)

Name those skills in every Task prompt — an mdc rule does not load into the child. Default subagent model: `cursor-grok-4.6-high-fast`. See `.cursor/rules/subagent-models.mdc`.

Do not evolve `archive/`. Do not resurrect the Expo client.
