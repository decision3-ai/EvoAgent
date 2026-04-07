# AgentEvo — V2+ Roadmap

---

## V2 — Fitness

Background layer: formal scoring, workers, metrics, pipelines that turn feedback into measurable fitness.

### Planned
- [ ] NEAR wallet auth (full integration)
- [ ] Celery fitness worker
- [ ] LangGraph evolution pipeline (background)
- [ ] Formal fitness metrics surfaced from stored feedback
- [ ] fitness_score normalization and formula expansion (iteration bonus, correction penalty, code bonus)

---

## V3 — TBD

- [ ] NEAR smart contracts for agent NFTs
- [ ] Agent marketplace
- [ ] Analytics dashboard

---

## V4 — TBD

*(Assign items when roadmap is fixed.)*

---

## Notes

- V2 plugs into V1 Core without modifying it — Plugin reads Core tables, Core never imports Plugin.
- Fitness V2 Phase 1 already done: `fitness_score` field on `Message` table, populated from thumbs up/down feedback.
