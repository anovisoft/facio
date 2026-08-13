# Blueprint Storage

## Requirements

- strong versioning
- schema validation
- fast read by id/version
- publish workflow
- diffability for reviewers
- localization of user-facing strings
- separation of structure vs media content

## Storage recommendation

### Source of truth: Git + registry

Author blueprints as validated YAML/JSON in a **content repo** (or `/blueprints` in monorepo).

CI:

- JSON Schema validation
- simulation tests
- safety lints
- compatibility checks

CD:

- publish immutable artifact to Blueprint Registry (object storage + DB index)

### Runtime: compiled documents in DB/CDN

```text
blueprints
  id
  version
  status (draft|staged|published|deprecated)
  schema_version
  content_hash
  compiled_json
  published_at
  editor_metadata
```

Apps/servers fetch by `(id, version)` with CDN caching.

### Why Git-backed authorship beats DB-only CMS early

- code review culture
- diffs
- rollbacks
- tests alongside content

Add a friendly CMS UI later that still emits versioned artifacts.

## Content vs structure split

| Store in blueprint | Store as content references |
|--------------------|-----------------------------|
| stages, unlock rules | long exercise instructions |
| dose formulas | video URLs |
| adaptation predicates | recipe narratives |
| intake schema | images |

This keeps blueprints small and reusable across locales.

## Localization

- structural IDs stable across languages
- string tables: `title`, `action_name`, `why_it_matters`
- locale fallback chain

Do not fork entire blueprints per language unless rules differ culturally (they sometimes will).

## Validation layers

1. **Schema** — required keys, types
2. **Graph** — no unlock cycles; all node refs resolve
3. **Dose** — ranges sane
4. **Policy** — sensitive domains need acknowledgements
5. **Simulation** — persona dry-runs produce schedules
6. **Budget** — estimated actions/week within contract claims

## Publishing API (internal)

- `validate`
- `stage`
- `publish`
- `deprecate`
- `migrate_project` (rare, explicit)

## Client offline pack

For execution reliability:

- download compiled blueprint + next N actions for active projects
- offline mark done → sync later

Coach may be online-only.

## Critique: storing blueprints only as “prompt templates”

If a blueprint is just a big system prompt, you have:

- no deterministic execution
- no testable unlock rules
- no cheap adaptation
- no real flywheel

Prompts can *assist authoring*. They must not *be* the blueprint format.
