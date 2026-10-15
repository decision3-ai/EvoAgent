# ROADMAP — EvoAgent

Samo budući plan. Završeno → `CHANGELOG.md`. Tehnički detalji → `ARCHITECTURE.md`. Ideje bez odluke → `IDEAS.md`.

Cilj oktobra 2026: stabilan, siguran proizvod koji agencije (5–50 ljudi) mogu stvarno koristiti.

---

## 🔴 SAD

### 1. Sigurnost (prije svega ostalog)

**1a. NEAR Wallet Auth — prava kriptografska provjera** (bivši V4.1)

Zamijeniti trenutni nepotpisani NEAR stub u `core/auth.py` pravom verifikacijom.

Backend:
- `POST /api/v1/auth/near/nonce` — generiše jednokratni nonce (Redis, 5min TTL)
- `POST /api/v1/auth/near/verify` — provjerava ed25519 potpis, izdaje JWT sa `sub=near:{account_id}`
- `core/auth.py` — ukloniti nesigurni pass-through; JWT je jedini auth put
- Bez novih DB tabela — `user_id` već podržava bilo koji string (`near:alice.testnet` ili `email@example.com`)

Frontend:
- `contexts/near-wallet.tsx` — `connectNear()`: nonce → `wallet.signMessage()` → verify → spremi JWT
- `components/near/connect-wallet-button.tsx` — prikazati NEAR wallet dugme (trenutno skriveno)

Mreža: prvo testnet (`evoagent.testnet`), jedna promjena configa za mainnet (`evoagent.near`)

**1b. EvoSmart zaštita**
- `POST /api/v1/evosmart/chat` je javan, bez JWT-a — bilo ko troši Gemini kredit
- Dodati rate limit po IP-u (Redis) i dnevni limit ukupnih poziva

### 2. Web Search
- Serper API kao LangGraph alat
- Agent sam odlučuje kad treba tražiti

### 3. Confidence Scoring
- Agent ocjenjuje svoju sigurnost u odgovor (1–10)
- Ispod 7 → automatski pokreće Web Search

---

## 🟡 SLJEDEĆE

### Code Execution
- Sandbox za izvršavanje koda koji agent napiše

### Multi-agent + LangGraph orkestracija (bivši V4.5)
- Više agenata po workspace-u, delegiranje zadataka
- LangGraph pipeline za složeno razmišljanje u više koraka

### Analytics Dashboard
- Performanse agenta, fitness trendovi, istorija EvoPoints
- Prvi korak upsell puta

---

## 🔵 KASNIJE

### Knowledge Graph
- Veze između entiteta (ljudi, projekti, firme) u memoriji agenta

### Agent Marketplace (bivši V4.3)
- Pregled i pokretanje agenata zajednice
- Vlasništvo i revenue sharing — blockchain dio je u `IDEAS.md`

---

## Pravilo
Kad ideja iz `IDEAS.md` dobije 🟢, ulazi ovdje. Kad stavka bude gotova, seli se u `CHANGELOG.md`.
