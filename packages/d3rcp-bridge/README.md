# D3RCP Bridge

D3RCP — payment bridge that turns AI agent requests into real x402 micropayments on Algorand mainnet.

## How it works

Express server running on port 4500. EvoAgent's Python API posts `{ sessionId, userId }` to `POST /d3rcp/pay`, and the bridge executes the full 5-stage Interouter payment lifecycle via `AlgorandAdapter`:

```
readState → preparePayment → sign → submit → awaitFinality
```

The bridge is stateless — no database, no persistent state. It returns `{ txHash, finalized, accepted }` to the caller and never blocks the chat response.

## Verified mainnet transaction

First live x402 payment on Algorand mainnet:
https://allo.info/tx/WV3HKGS2HQVGQ7LURTUBRIYBUA73UOC3632U6S3YXUBTKUODHK2A

## Environment variables

```
ALGORAND_BUYER_MNEMONIC      # 25-word mnemonic for the buyer wallet
D3RCP_RESOURCE_ENDPOINT      # URL of the x402-gated resource (e.g. http://localhost:4021/api/inference)
ALGORAND_ALGOD_URL           # Algorand node URL (default: https://mainnet-api.algonode.cloud)
```

## Running

```bash
cp .env.example .env
# Fill in the values above
npx tsx server.ts
```

## Part of the Decision3 ecosystem

Built on [`@decision3/interouter-core`](https://www.npmjs.com/package/@decision3/interouter-core) — the Interouter protocol implementation for x402 payments across chains.
