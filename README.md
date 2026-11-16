# CiteTrace — versioned claim reviews

Live app: https://genlayer-proofwork.sillynightingale1.chatgpt.site/citetrace

Contract (Bradbury Phase 2, chain 4221): https://scan.bradbury.genlayer.com/address/0x9D34993A82039478b496a2fAe403BA12DD6e14AA

CiteTrace is a complete public workspace for a specific problem: a text claim can receive supporting evidence today and counterevidence tomorrow, while a single editable verdict hides how the evidence changed. Here, each evidence snapshot and classification is immutable. New evidence opens a child round; the original result remains visible and shareable.

## Use the application

1. Open the live app without a wallet to inspect public reviews. Choose a review and switch rounds to compare their committed evidence and results. Copy a round-specific public link or export the full review as JSON.
2. Connect a Bradbury testnet wallet. Choose **New review**, enter a precise claim, source reference and original excerpt, and commit the review. Text is public; do not upload private material.
3. The round author chooses **Resolve this round**. GenLayer validators independently classify every excerpt as `supports`, `contradicts` or `insufficient`. Each classification must be complete, reference a valid source and use an actual source quotation.
4. On a resolved round, anyone may commit an additional excerpt. This creates a separate child round with all parent evidence plus the new source. Its author resolves it. Other branches remain usable even when one branch is awaiting resolution.

The browser signs and broadcasts through the user's own EIP-1193 wallet. The hosted Worker only serves assets and allowlisted public RPC reads/fee estimation; it does not hold private keys, sign, or broadcast. Pending transaction IDs persist locally, so reopening the page tracks the original transaction instead of resending. An unknown wallet response is retained for explicit transaction-ID reconciliation rather than silently retried. A receipt must be FINALIZED, MAJORITY_AGREE, accepted and FINISHED_WITH_RETURN before the UI reports success.

## What consensus does

The committed claim and evidence are untrusted text. The contract asks each validator to independently classify the **entire exact claim and scope**, ignoring instructions in source text. It validates complete one-to-one source coverage, strict IDs, enums and quote membership. Valid quotations are then canonicalized to entire original excerpts. The stable `strict_eq` wrapper compares the independently produced ID/relation decisions and deterministic evidence, allowing different valid substring selections without accepting different decisions.

Ordinary deterministic code computes a descriptive verdict: `support_only`, `contradiction_only`, `conflicted` (both relations exist), or `insufficient`. There is no majority vote by source count and no arbitrary trust score. SHA-256 snapshots bind the claim and cumulative evidence to each round. A round author can resolve only once; no method rewrites prior rounds, claims or excerpts.

Limits: 1–8 distinct references/excerpts per snapshot, 12 rounds per review, 1,200 characters per excerpt, 600 per claim. Parent rounds must already be resolved. New branches do not overwrite each other and do not require a globally latest-round race. Public append is not a Sybil-resistance mechanism; spam can exhaust a review's bounded round capacity, in which case an independent review can be created. There is no moderation or deletion mechanism in this prototype.

## Scope and limits

The application evaluates **the relationship of supplied text to a claim**, not the truth of the claim or authenticity of its sources. References are contributor labels and are not fetched or verified. Consensus can agree on an incorrect semantic classification. A quotation's membership proves provenance within the committed text, not that its author is trustworthy. “Support only” is not a fact-check badge. Do not use this prototype for high-stakes decisions.

The seeded Workshop Orion review uses explicitly labelled **synthetic test fixtures**, submitted and resolved by one builder wallet. It does not represent a real workshop, independent participants, source adoption or production users. No usage, rewards or token returns are claimed.

## Reproduce the contract workflow

```sh
python tests.py
npm ci --ignore-scripts
node --test receipt-policy.test.mjs
# Set GENLAYER_PRIVATE_KEY_FILE to your own ignored Bradbury test wallet key file.
npm run deploy
npm run demo
```

`demo.mjs` commits a synthetic 09:00 opening claim, resolves the supporting original excerpt, appends an explicit 11:00 correction as a child round, then resolves the now-conflicted cumulative evidence. It asserts both the new result and preservation of the original support-only round. It refuses a duplicate start. An interrupted run must be reconciled with `node scripts/run.mjs`; never blindly rerun the demo.

The backend scripts verify chain ID, genesis and manager, cap signed transactions at 0.3 test GEN, protocol deposit at 0.2 and session balance loss at 1. SDK versions are pinned. Keys, logs and signer state are ignored. Public receipts and finalized state are published separately after successful execution.

24 Python business-rule tests cover evidence coverage, exact quotations, source/round limits, deduplication, creator/round-author permissions, public counterevidence, immutable resolution, parent eligibility, independent branches, numeric IDs, source relationship enums, snapshot preservation, atomic failure and independent consensus disagreement. Four Node receipt regressions reject majority-disagree, VM errors and unfinalized receipts. Python's local SDK stub exercises deterministic rules and independent-output comparison, not the real network; the separate live demo verifies actual GenVM/validator behavior.

## Reproduce the frontend

`web/` contains the standalone browser app and a minimal keyless Worker build. Install its pinned dependencies, run `npm run build`, then `npm run preview` in that folder. It serves the app at `/citetrace` and relays public RPC requests to the official Bradbury endpoints. Update the public contract constant only if you deploy your own instance. No runtime secret is required.

## Evidence

`deployment.json`, `first-round.json` and `demo-result.json` document the finalized transactions, original snapshot and resulting review history. Browser QA and submission evidence are recorded locally in `submission-status.json` once performed. Any Portal award is reported only after actual approval.

The live demo was verified on 16 November 2026: round 1 remained `support_only`; child round 2 became `conflicted`, with source 1 supporting and source 2 contradicting. All five transactions (deployment plus four workflow writes) finalized with majority agreement, accepted outcome and successful execution. `node read.mjs` verifies the published state using a public account address and no private key.

| Operation | Net test GEN after final refunds |
|---|---|
| Deployment | 0.000143837330002117 |
| Create review | 0.000084177880002117 |
| Resolve original round | 0.000082930080001764 |
| Append counterevidence round | 0.000083720680002117 |
| Resolve counterevidence round | 0.000083399580002117 |

An initial create+resolve interaction used **0.000167107960003881 test GEN**. The subsequent counterevidence+resolve interaction used **0.000167120260004234**. The complete four-write history workflow used **0.000334228220008115**; including deployment, **0.000478065550010232**. Costs are observed balance deltas from an otherwise idle builder test wallet, not reward estimates or real-token expenditure.

MIT license. This project is a new full application; it does not reuse or resubmit the previously submitted standalone contracts.
