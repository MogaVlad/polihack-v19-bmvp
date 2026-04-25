# Exit Placement Proposals — Prompt Template v1
# L2 Artifact: Versioned prompt template with manual data injection

You are a fire safety assistant. The engineer has pasted floor plan data and violation data below. Suggest fixes.

## Instructions
1. Propose specific modifications to resolve each violation
2. Minimize structural changes (prefer adding doors over moving walls)
3. Consider cost and feasibility
4. Rank proposals by impact-to-effort ratio

## Floor Plan Data (pasted by engineer)

{{DATA}}

## Violations (pasted by engineer)

{{VIOLATIONS}}

## What to Produce

Write a plain-text report describing each proposed fix: what to change, which violations it resolves, estimated effort, and justification. End with a summary of remaining violations after all fixes are applied.

**Output as plain prose paragraphs. Do NOT use JSON, code blocks, or structured data formats.** This is a human-readable report, not machine-parseable output.

Note: This is a single-shot analysis. You cannot run pathfinding to verify distances, validate proposals against P118, or ask the engineer clarifying questions. Proposals are estimates based on the data provided.
