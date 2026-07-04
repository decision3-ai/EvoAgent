/**
 * D3RCP Payment Bridge — Decision3 Routing Context Protocol
 *
 * Purpose: FastAPI (Python) cannot call AlgorandAdapter directly — it's
 * TypeScript. This is the thin, stateless bridge: Python POSTs here,
 * this process runs the already-verified 5-stage Interouter payment
 * lifecycle against the mainnet resource server, and returns the result.
 *
 *   EvoAgent (Python, chat/router.py)
 *        │  POST /d3rcp/pay { sessionId, userId }
 *        ▼
 *   THIS BRIDGE (Node)
 *        │  readState → preparePayment → sign → submit → awaitFinality
 *        ▼
 *   AlgorandAdapter → GoPlausible facilitator → Algorand MAINNET
 *
 * This bridge does NOT store anything — no DB, no log file. sessionId
 * and userId are echoed back in the response so Python (which already
 * owns the users/sessions tables) can write its own payment audit row.
 * That keeps one source of truth instead of two logs that can drift.
 *
 * Uses the SAME buyer wallet + mainnet resource server already verified
 * in commit 6e7c40b (txHash 3PU3QEIBW4CIBENLT5ZOI25QIO3DBEVAWCDTSYPWDKZQTRIKKPFA).
 * No new wallet, no new server — this just gives Python a door to knock on.
 *
 * ⚠️ CONFIRM before wiring in (ask CLI to check, don't guess):
 *   Does this package's package.json resolve "@decision3/interouter-core"
 *   via the pnpm workspace (workspace:*), or does AlgorandAdapter need to
 *   be imported by relative path instead? Check pnpm-workspace.yaml.
 *
 * Run:
 *   npm install express
 *   ALGORAND_BUYER_MNEMONIC="<mainnet buyer mnemonic>" \
 *   D3RCP_RESOURCE_ENDPOINT="http://localhost:4021/api/inference" \
 *   npx tsx d3rcp-bridge-server.ts
 */

import express from "express";
import { AlgorandAdapter } from "@decision3/interouter-core"; // CONFIRM import path — see note above

const app = express();
app.use(express.json());
const PORT = Number(process.env.D3RCP_PORT ?? 4500);

const mnemonic = process.env.ALGORAND_BUYER_MNEMONIC;
if (!mnemonic) {
  throw new Error("D3RCP bridge: ALGORAND_BUYER_MNEMONIC is required — refusing to start without it.");
}

const adapter = new AlgorandAdapter({
  mnemonic,
  resourceEndpoint: process.env.D3RCP_RESOURCE_ENDPOINT ?? "http://localhost:4021/api/inference",
  algodUrl: process.env.ALGORAND_ALGOD_URL ?? "https://mainnet-api.algonode.cloud",
});

interface PayRequestBody {
  sessionId?: string;
  userId?: string;
}

app.post("/d3rcp/pay", async (req, res) => {
  const { sessionId, userId } = (req.body ?? {}) as PayRequestBody;

  // These aren't used by the payment itself — they're required so whatever
  // calls this bridge is forced to identify the real request behind the
  // payment. This is the "proof of who is paying for it" trail the x402
  // Challenge rules ask for (no anonymous/looped calls to this endpoint).
  if (!sessionId || !userId) {
    return res.status(400).json({ error: "sessionId and userId are required" });
  }

  const context = { path: "/api/inference", params: { sessionId, userId } };

  try {
    const read = await adapter.readState(context);

    // Resource wasn't gated this call (shouldn't normally happen for a
    // COMPLEX-classified request, but handle it rather than crash).
    if (read.paymentRequired === null) {
      return res.json({
        sessionId,
        userId,
        accepted: true,
        txHash: null,
        finalized: true,
        result: read.state,
      });
    }

    const payload = await adapter.preparePayment(read.paymentRequired);
    const signed = await adapter.sign(payload);
    const submission = await adapter.submit(signed, context);
    const finality = await adapter.awaitFinality(submission);

    return res.json({
      sessionId,
      userId,
      accepted: submission.accepted,
      txHash: finality.txHash,
      finalized: finality.finalized,
      result: finality.state,
    });
  } catch (err) {
    const message = err instanceof Error ? err.message : String(err);
    // Fail closed: Python should treat this as "payment did not go through"
    // and not run the Claude polish step.
    return res.status(502).json({ sessionId, userId, accepted: false, error: message });
  }
});

app.get("/health", (_req, res) => res.json({ ok: true, service: "d3rcp-bridge" }));

app.listen(PORT, () => {
  console.log(`D3RCP payment bridge on :${PORT}`);
  console.log(`  POST /d3rcp/pay  { sessionId, userId }`);
  console.log(`  GET  /health`);
});
