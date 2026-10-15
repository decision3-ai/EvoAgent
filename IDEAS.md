# IDEAS.md — Decision3 registar ideja

Statusi: 🟢 Aktivno · 🟡 Na čekanju · 🔵 Dugoročna vizija · 🔍 Istraženo / referenca · ⚫ Odbačeno · ❓ Potvrdi status

Pravilo: nova ideja ide ovdje ODMAH, makar u jednoj rečenici. Status se mijenja, ništa se ne briše — odbačeno ide u ⚫ sa razlogom.

---

## Proizvodi

| Ideja | Status | Kratko |
|---|---|---|
| **EvoAgent** (evoagent.io) | 🟢 | SaaS za agente koji uče kroz feedback. Cilj: firme i agencije 5–50 ljudi. Oktobar 2026 = odlučujući mjesec. |
| **EvoCare.io** | 🟡 | AI agenti za starije (65+): Health, Finance, Home + "Family Loop". B2C $29–49/mj, white-label za osiguranja, B2B za domove. Na EvoAgent Core. |
| **Interouter** | ❓ | Open-source Node.js middleware: Next.js SSR → blockchain (x402 / NEAR plaćanja). |
| **Decision3 Console Air** | ❓ | White-label fork Akash Console Air na deploy.decision3.ai. Stack: AkashML → EvoAgent → Console. |
| **EvoSyn** (evosyn.com) | ❓ | Lični AI agent sa trajnom memorijom i granicama povjerenja. |
| **AgentEvo job-search agent** | ❓ | "Done-for-you" agent za automatizaciju traženja posla (voice bot projekat). |
| **EVO token-gating** | ❓ | Pristup EvoAgentu preko NEAR EVO tokena. |
| **Behavioral prediction AI** | 🔵 | Mapiranje pokreta sportista (boks, fudbal) da se predvidi sljedeći potez. Poseban proizvod, ne EvoAgent feature. |
| **EvoS3** | 🔵 | Otvorena platforma gdje treći lansiraju agente (kao Bio.xyz za business ops). |
| **Coding kurikulum na BHS** | ❓ | Kurs od HTML-a do React/Vue za ljude koji ne znaju engleski. |

## EvoAgent — feature ideje

| Ideja | Status | Kratko |
|---|---|---|
| Web Search (Serper + LangGraph) | 🟢 | Prioritet 1 na roadmapu. |
| Confidence Scoring (1–10) | 🟢 | Ispod 7 automatski pokreće pretragu. |
| Code Execution (sandbox) | 🟢 | U ROADMAP-u (SLJEDEĆE). |
| Knowledge Graph | 🟢 | U ROADMAP-u (KASNIJE). |
| Upsell: Analytics → Marketplace → Connectors → White-label | 🔵 | Put rasta prihoda. Analytics i Marketplace su u ROADMAP-u. |
| GEO/AEO (citiranje u ChatGPT/Claude/Perplexity) | 🟡 | 3 koraka čekaju: `llms.txt`, JSON-LD schema, provjera robots.txt/Cloudflare. |
| Self-hosted modeli na Akash (Qwen3.6-27B) | 🟡 | Pauzirano zbog cijene GPU-a; sada Claude preko OpenRoutera. |
| Browser agent (Kimi WebBridge koncept) | 🔍 | Agent koristi korisnikov ulogovani browser. Za V4 / EvoCare. |

## EvoAgent — blockchain sloj (izvučeno iz starog ROADMAP V4)

| Ideja | Status | Kratko |
|---|---|---|
| **NEAR smart ugovori** (bivši V4.2) | 🟡 | On-chain registar agenata (workspace metadata na NEAR-u). Ugovor `evoagent.near` (Rust, NEAR SDK). |
| **EvoPoints kao on-chain token** (bivši V4.2) | 🟡 | EvoPoints kao NEAR FT standard token. |
| **Evolution audit trail** (bivši V4.2) | 🟡 | Evolution događaji zapisani on-chain, nepromjenjivo. |
| **Marketplace na blockchainu** (bivši V4.3) | 🟡 | Vlasništvo agenta vezano za NEAR nalog, revenue sharing preko smart ugovora. |
| **Walrus/Sui storage** (bivši V4.4) | 🟡 | Memorija i sesije na Walrusu, pod korisnikovim NEAR/Sui ključem. PostgreSQL za svježe podatke, Walrus za dugoročnu arhivu. |

Uslov za 🟢: plaćeni korisnici koji to stvarno traže.

## Biznis / infrastruktura

| Ideja | Status | Kratko |
|---|---|---|
| Registracija j.d.o.o. | ❓ | Najrealniji put za naplatu softvera u Hrvatskoj. |
| GPU rigovi + iznajmljivanje compute na Akash | 🔵 | Lokalno pokretanje EvoAgenta + prihod od compute-a. |

## Istraženo (tehnologije i partneri)

| Šta | Status | Zaključak |
|---|---|---|
| **Phala Network** | 🔍 | Privatna inferenca na TEE GPU-ovima. Kandidat za EvoCare (zdravstveni i finansijski podaci). |
| **Orbio** (Robinhood Chain) | 🔍 | Plugin za Claude Code, sve se plaća u $CREDIT. Mlad projekat, anonimni osnivači. Ne donosi ništa što već nemamo. |
| **Midnight** (ZK blockchain) | 🔍 | MIRROR projekat — istraživanje privatnosti. |
| **Billions Network** | 🔍 | Identitet za AI agente. Prerano dok EvoAgent ne radi high-stakes zadatke. |

---

## Inbox (brze ideje — razvrstaj kasnije)

- 
