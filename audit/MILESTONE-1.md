# CiteTrace milestone: independent lineage replay and anchored export audit

Accepted Project: CiteTrace, https://portal.genlayer.foundation/contribution/266284

Baseline source: d5aba20bcb7bfb9176f3f6b1b028f7853299228c (original full application).

## New behavior

The original application displayed rounds and exported JSON. A recipient still had to trust its rendering, a hand-written summary, or an arbitrary exported file. This milestone adds an independent Python standard-library auditor plus a keyless final-state reader. It replays every round, checks the actual parent branch rather than assuming the previous array element is the parent, rejects rewritten inherited evidence, reconstructs verdicts and witness lists, and reports changes in the classifications of inherited sources.

`verify.py` recomputes the exact Python canonical SHA256 used by the contract, including Unicode. It validates full source coverage, canonical quote contents, contiguous round IDs, branch ancestry, committed-versus-resolved states and summaries. Duplicate JSON keys and nonfinite numbers are rejected. An optional separately fetched anchor compares the **entire** review, including title, authors and verdicts that the source snapshot hash alone does not bind. This catches a self-consistent forged export as well as a simple hash mismatch.

## Reproduce without a private key

From repository root, install existing pinned Node dependencies if needed (`npm ci --ignore-scripts`). Python needs no third-party packages.

```sh
python -m unittest discover -s audit -v
node audit/fetch.mjs 1 audit/fresh-anchor.json
python audit/verify.py audit/live-review-1.json --anchor audit/fresh-anchor.json
```

To audit a new review, use its ID in `fetch.mjs`. Audit a browser-exported single review JSON by passing its path in place of `audit/live-review-1.json`. A locally supplied anchor is only as trustworthy as its origin: generate it yourself using the keyless reader, which requests `transactionHashVariant: latest-final` from the official Bradbury RPC and the fixed deployed CiteTrace address. There is no caller-supplied contract or endpoint and no write/signing code.

## Verified results (23 November 2026)

10 unittest methods passed, including 16 distinct adversarial mutation subcases, a rehashed inherited-source rewrite, valid sibling branches, Unicode, duplicate keys, semantic reclassification, pending child handling, full-record anchor comparison and a self-consistent forged title.

Two independent latest-final reads of real deployed review 1 agreed. The new auditor independently reconstructed round 1 `support_only`, round 2 `conflicted`, parent 1, and one added counterevidence source. Snapshot hashes were `26658c161cc04fda661ed42b8dfd219d6ce136bf18d7d8b21d28a13151addc63` and `0030adf7a544561e721e5c985fbb50173753e7263cd9aecd48e33dd70db49ab1`. The committed example is explicitly synthetic and uses one builder wallet; it is not evidence of real user adoption.

No new contract, deployment, signature, or write transaction was needed. New test GEN expenditure: **0**. Existing contract consensus was not rerun; semantic truth and source authenticity are not verified. The anchor is an RPC trust boundary, not a cryptographic light client or proof of historical chain inclusion. This milestone is a backend verification improvement; the hosted frontend is unchanged.
