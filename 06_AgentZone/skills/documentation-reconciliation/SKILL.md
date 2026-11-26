---
name: "documentation-reconciliation"
description: "Reconcile existing documentation with authoritative standards, merged changes, independent verification, and current work tracking while preserving its format and scope."
---

# Documentation reconciliation

1. Apply [Prevent Drift](../prevent-drift/SKILL.md). Use [Session Handoff](../session-handoff/SKILL.md) to find the latest shared handoffs and roadmap on the default branch. Read the applicable standards directly when your context provider does not supply them.
2. Verify claims against their sources. Use merged changes in the code host for implementation, independent CI on the relevant revision for verification, the work tracker for workflow state and owner decisions, and operational evidence for live behavior. Check the status inventory or a formal re-grade before updating scores. Treat handoffs as leads and flag material disagreements or missing evidence.
3. Correct only claims whose status, date, or wording the evidence supports. Distinguish planned, implemented, integrated, independently verified, and operationally verified work. Scope verification to what actually ran. Distinguish a capability exercised manually from one that runs automatically. Keep private implementation and retrieved context out of public documentation.
4. Keep the document's voice, headings, section order, formatting, and layout. Edit in place. Preserve images, diagrams, badges, embeds, tables, and progress bars. Change metrics or labels only with evidence. Compare the diff with the original before publishing.
5. Use [PR Hygiene](../pr-hygiene/SKILL.md) to publish through the existing authorized change route and check independent CI where available. Keep human merge authority. Record unresolved evidence or publication blockers through the existing handoff.
