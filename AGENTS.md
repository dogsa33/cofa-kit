# Cofa Ready Kit (standalone, preparation only)

This AGENTS.md governs maintenance of this public kit repository; **never copy it over the actual task AGENTS.md**.

- The actual task brief, organizer restrictions, and provided files take precedence.
- Main Codex only: no subagents, parallel delegation, MCP installation, or global Codex configuration changes by default.
- Preserve original task input data, expected output schemas, and user changes.
- Ask the participant **one material decision at a time**; AI recommendation is not participant approval. Explicit choice before choice-dependent final implementation. Test PASS/FAIL is never a design choice.
- Within an approved scope, implement routine details, test, and repair without repeated approval. Keep files, dependencies, and documentation minimal.
- Do not mark dropped, skipped, stale, or untested mandatory requirements as verified. No tests means no test success.
- Manual Browser UAT is participant-operated. Do not automate the browser or fabricate observed results.
- Keep all data local; do not push exam data/logs, credentials, or personally identifying inputs.
- The official Cofa timer prevails over the terminal clock; use the 180-minute phase targets in `prompts/SCENARIO.md` as flexible budgets, not hard stops. Target a first integrated build by 120 minutes and preserve the last 10 minutes for submission. Never invent remaining time or silently drop mandatory requirements.
- Once submission is confirmed, stop AI workflows. Post-submission written response is participant-only.
- For source changes to this kit, run `python -X utf8 -m unittest discover -s tests -v`.
