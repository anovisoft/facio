# Facio

A personal product I build and run: an assistant answer is easy to get and impossible to keep, so Facio
gives it somewhere to live. A practice you decided to do becomes a subject with a cadence, cues and a
window, and the system works out on its own when you are drifting from it.

Python domain library, FastAPI backend, SwiftUI iOS client.

---

## Start here: `packages/domain`

If you are looking at this repository to see how I work, open this package first. It is the law of the
product as pure functions, and the tests are the part worth reading.

**Over 300 tests, and no network, no model, no database.** Cadence, computed drift, reminder
windows, ranking, freeze and retire transitions, the projection that decides what is due now.

The test names are the specification:

```
test_never_started_subject_is_not_drift
test_cadence_none_without_instances_is_not_drift
test_bike_fixture_window_matches_founding_rule
test_done_widget_other_day_leaves_today
test_freeze_retired_is_invalid
test_create_widget_tick_on_new_subject_does_not_spawn_reminder
```

Two decisions in there that I would defend in a review:

**Fixtures are the single source of truth across two languages.** `packages/domain/fixtures/*.json`
is run by the Python tests and by the Swift client. If the two disagree, that is a release hole, not
a rounding difference.

**The schema is an exported contract, not a hand-written document.** `facio-export-schema` writes
JSON Schema from the Pydantic models into `packages/schema`, and CI fails if the committed copy differs
from what the models produce, so the contract cannot drift from the code behind it without the build
saying so. The iOS client is held to the same law by the fixtures above, not by this schema.

Run them:

```bash
python3 -m venv packages/domain/.venv
source packages/domain/.venv/bin/activate
pip install -e packages/domain
pytest packages/domain
```

---

## Map of the repository

| Path | What it is |
|---|---|
| `packages/domain` | The domain law. Pure functions, fixtures shared with the iOS client. **Start here.** |
| `apps/api` | FastAPI backend over the domain package. Providers behind interfaces, golden tests on the API surface. |
| `apps/mobile-swiftui` | The iOS client. A port of the domain law, run against the same fixtures. |
| `docs/rfc` | Design documents, written before the code. Vision, principles, domain model, and `06-never-do.md`. |
| `docs/state` | The engineering memory: what was tried, what broke, what is still open. Russian. |
| `.github/workflows` | CI. Domain and API tests on every pull request, the iOS suite on pull requests into `main`. |
| `archive/` | An earlier backend, superseded and kept for reference. Not part of the current build. Roughly a third of the tracked files in this repository sit here, so ignore it unless you are curious about where this came from. |
| `AGENTS.md`, `.cursor/` | How I drive AI tooling on this codebase, committed next to the code it applies to. |

---

## On the documents

`docs/rfc` is written first and the code follows. `06-never-do.md` exists because the useful half of a
specification is the part that says what the system will refuse to do. Those documents are in English,
as is the code. `docs/state` is the engineering memory next to them — what was tried, what broke, what
is still open — and it is in Russian, which is my working language on personal projects.

---

## On AI tooling in this repository

The rules I give models live in `AGENTS.md` and `.cursor/`, in version control, next to the code. A
model reads unfamiliar code, writes tests and does mechanical refactors here. It does not touch the
domain package without me reading every line, because those functions are the ones with exact expected
outputs, and a plausible answer is worse than no answer when the fixtures are the contract.
