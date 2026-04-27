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

## V2.3 — Async Pipeline (Preduvjet za V3)

Cilj: Redizajnirati trenutni sinkroni pipeline gdje evolve_agent radi blokirajuće u asinkroni sustav koji koristi Queue.

### Zašto

- `evolve_agent` trenutno blokira worker dok čeka LLM odgovor (10-15 sekundi)
- Nightly beat ne može paralelno procesirati više agenata
- V3 Persistent Agent zahtijeva non-blocking execution

### Što treba

- [ ] `evolve_agent` postaje fire-and-forget task
- [ ] Rezultati se vraćaju kroz Redis/callback, ne direktno
- [ ] Worker pool može procesirati više evolucija paralelno

---

## V3 — Persistent Agent (Pravi Kontinuitet)

Cilj: Agent koji aktivno prati projekat, ne čeka da ga korisnik vodi.

### Funkcionalnosti

- [ ] **Persistent Memory Layer** — agent čuva zaključke, odluke, upozorenja u bazi (ne samo chat historiju)
- [ ] **Proactive Monitoring** — ARQ worker periodično skenira kod i metrics, upozorava korisnika bez da pita
- [ ] **Architectural Goal Tracking** — agent mjeri svaki commit prema ciljevima iz CLAUDE.md
- [ ] **Multi-session Context** — agent zna što je rađeno jučer, prošle sedmice, gdje je korisnik zapeo
- [ ] **Walrus/Sui integracija** — podaci korisnika na decentralizovanoj mreži

### Filozofija

Ne coding partner koji odgovara — agent koji te aktivno prati i vodi.

---

## V4 — TBD

*(Assign items when roadmap is fixed.)*

---

## Notes

- V2 plugs into V1 Core without modifying it — Plugin reads Core tables, Core never imports Plugin.
- Fitness V2 Phase 1 already done: `fitness_score` field on `Message` table, populated from thumbs up/down feedback.
