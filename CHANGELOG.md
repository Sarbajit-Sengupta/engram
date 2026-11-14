# Changelog

All notable changes to this project will be documented here.

Format: `type: description (#PR or #issue)`
Types: `feat` · `fix` · `test` · `docs` · `chore`

---

## Unreleased

_PRs merged to `main` but not yet released._

- test: cover empty input, multi-sentence storage, dataset isolation, forget and prune edge cases (#10)

---

## 0.1.0 — 2026-11-12

- feat: initial public release — `remember`, `recall`, `prune`, `forget`, `improve`
- feat: Ebbinghaus decay with configurable global rate (`ENGRAM_DECAY_RATE`)
- feat: sentence-level extraction and storage
- feat: knowledge graph for entity relationships
- feat: vector index for semantic search
- feat: `MetaStore` SQLite backend
