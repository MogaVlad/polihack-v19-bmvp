# Hackathon Project Brief: Fire Safety Evacuation Copilot

## Context

We're competing in the "App Dev with AI" division of a hackathon themed around **AI adoption in engineering — tools to transformation**. The brief emphasizes that AI adoption is a mindset and operating-model change, not just tool usage, and challenges teams to pick an engineering field where AI adoption is lacking and build something that genuinely shifts how work gets done.

An example that fit the theme well: for architecture engineering, a tool that optimizes an existing house floor plan and renders a realistic visualizer. That's the shape we're copying — upload a domain artifact, AI does the hard intellectual work, produce a compelling visual output.

## What we're building

**An AI-native fire safety and evacuation copilot for architects, as a Python desktop application (Tkinter).**

An architect uploads a floor plan (image or PDF). The app:

1. Uses a vision LLM to parse the plan into structured data (rooms, doors, corridors, exits, walls) and can export to multiple formats
2. Validates the parsed plan against **Romanian fire safety regulations** — checking for code violations (travel distance, dead-end corridors, exit capacity, door widths) and structural anomalies (blocked rooms with no exit, inaccessible areas, nonsensical corridor layouts)
3. Reports metrics: compliance status, violation list with severities, structural issues
4. Uses an LLM to diagnose problems in plain language and **propose** specific plan modifications (does not apply them automatically — the architect reviews and decides)

The demo moment: upload a floor plan → see violations light up on the canvas → click "AI Diagnose" → read concrete fix proposals ranked by impact → architect stays in control.

## Why this field and why this problem

Fire safety engineering is a real, regulated discipline almost entirely untouched by modern AI tooling. Academic papers from 2025 explicitly call out the gap: existing tools (Pathfinder, MassMotion, FDS) are desktop-based, expensive, require a trained specialist, and are too slow for rapid design iteration. Architects get fire safety feedback weeks later from outsourced consultants, so they don't iterate on it during design — they just hope the plan passes review.

Our wedge: put that feedback on the architect's desktop, during design, in seconds. We don't compete with Pathfinder for the final specialist review. We own the 50 earlier design iterations that never get checked today.

## Positioning for judges

**Theme fit** — Fire safety is a genuinely underserved engineering domain (evidence: Inspect Point 2025 industry report, SFPE AI Summit 2025 at UC Berkeley, multiple 2025 academic papers). Our app changes *how* architects work, not just which tool they use — that's the "tools to transformation" thesis.

**Market** — $75B+ global fire protection market, $12B AEC software market, 46% of Q1 2025 construction tech investment going to AI. Every commercial building on earth requires fire egress review, so the use case is mandatory, not optional.

**Differentiation** — Pathfinder and peers target fire protection engineers, on desktop, with trained modelers, using clean BIM inputs, producing simulation reports. We target architects, with zero training, from messy sketches/images, producing diagnosis + proposed fixes. The AI reasoning layer that validates against real Romanian regulations and proposes actionable fixes is the real novelty — no competitor does this.

**Pitch one-liner:** *"Every commercial building on earth has to prove people can escape it. Today that proof comes weeks later from a specialist. We give it to the architect in seconds, on their desktop, while they're still drawing."*

## Technical architecture

**AI does:** floor plan parsing (vision LLM → structured JSON, exportable to other formats), diagnosis of validation results (text LLM), fix proposals (text LLM → ranked list of proposed modifications).

**Classical code does:** validation against Romanian fire safety regulations — travel distance checks, exit capacity calculations, dead-end detection, blocked-room detection, corridor width verification, door count and placement rules. The architect reviews AI-proposed fixes and decides what to adopt.

**Stack:**
- GUI: Python + Tkinter (desktop application)
- Canvas: Tkinter Canvas widget for floor plan rendering + overlays
- LLM: Claude API with vision input for parsing, text for diagnosis
- Validation: Python rule engine checking against Romanian fire safety norms (P118, ISU regulations)
- No server required — runs locally, only external call is LLM API

**Data flow:**
```
[Floor plan image/PDF]
    → Vision LLM (parse to JSON: rooms, doors, exits, walls, corridors)
    → Structural sanity checks (blocked rooms, inaccessible areas, nonsensical geometry)
    → Romanian fire safety regulation checks (P118 norms: travel distance, exit capacity, door widths, dead-end corridors)
    → Collect violations + anomalies with locations and severities
    → Text LLM (diagnose in plain language + propose ranked fixes)
    → Display: canvas overlays + violation list + fix proposals
    → Architect reviews and decides
```

## Layout (desktop, single window)

Three-region layout:
- **Canvas (center, ~60%)** — floor plan rendering + overlay layers (violations, heatmap, diagnosis markers)
- **Agents panel (right, ~25%)** — four AI agents displayed as live status cards
- **Controls + metrics (top bar + left strip, ~15%)** — file picker, validation triggers, compliance summary

### Canvas
- Renders parsed plan: rooms, walls, doors, exits, corridors
- Zoom, pan, fit-to-window
- Overlay layers toggle: violations, heatmap, diagnosis markers
- Clickable violation markers linked to diagnosis list

### Agents panel (the L3 showcase)
Four agent cards: **PlanParser**, **EgressChecker**, **EvacDiagnoser**, **Redesigner**

Each card shows:
- Name and one-line job description
- State: idle / running / done / error
- Last output (expandable)
- Timestamp

Cards pulse/animate on state change so the processing sequence is visible. Click a card to inspect its definition (`agent.md`) and last structured output (JSON).

### Agent inspection (the L3 proof)
- Sidebar tab: "Agents" → browse all four agent definition files
- Each shows: scope, input schema, output schema, prompt, retry policy
- Run history per agent with structured outputs (for debugging + credibility during Q&A)

### Controls
- File picker: image, PDF, or JSON
- 2–3 pre-loaded example plans in a dropdown (demo safety net)
- Default plan loaded on app open

### Metrics strip
- Compliance status: N violations (color-coded by severity)
- Breakdown by category: travel distance, exit capacity, structural anomalies
- Overall pass/fail against Romanian P118 norms

### Diagnosis view
- Ranked list of problems from EvacDiagnoser
- Each item: location (clickable → highlights on canvas), severity, cause, recommended fix
- Linked to violation markers on canvas

### Fix proposals
- "Propose fix" button triggers Redesigner agent
- Shows proposed operations as a ranked list: *add exit at east wall, widen corridor B to 2.0m, add emergency door to room 7*
- Architect reviews — proposals are recommendations, not automatic changes

### Keyboard shortcuts
- `Space` — trigger validation
- `D` — diagnose
- `R` — reset view
- `F` — fit to window

## Scope — what we're building vs. cutting

**Must ship:**
- 2–3 pre-parsed example floor plans (hardcoded as JSON fallback in case live parsing fails)
- 2D top-down rendered floor plan on canvas with rooms, walls, doors, exits
- Validation against Romanian fire safety regulations (P118 norms)
- Structural anomaly detection (blocked rooms, dead ends, inaccessible areas)
- Metrics panel with violation counts and severities
- "AI Diagnose" button that returns plain-language problem descriptions
- "Propose fix" button showing ranked fix recommendations (not auto-applied)
- Agents panel showing the four AI agents with live status

**Stretch goals:**
- Live upload and parsing of arbitrary user floor plans via vision LLM
- Building type presets (office, school, restaurant, hospital) affecting occupancy density
- Export to multiple file formats from parsed plan
- Exportable PDF compliance report with violations and recommendations
- "Why this agent ran" trace — shows the event that triggered each agent

**Cut:**
- Multi-floor buildings (single floor only)
- Animated evacuation simulation (not in current scope)
- Real CFD smoke simulation
- Full regulatory code implementation (focus on core P118 rules)
- User accounts, saving, sharing
- Mobile support
- 3D view
- Auto-applying fixes (architect decides)

## Demo script (90 seconds)

1. "Every commercial building must pass fire egress review. Architects today get this feedback weeks later from a specialist." (10s)
2. Load example plan — a real-looking office floor. Show the agents panel: all four agents idle. (5s)
3. PlanParser activates → floor plan renders on canvas with rooms, corridors, exits labeled. Agent card shows "done." (10s)
4. Click validate → EgressChecker runs → violations light up on the canvas: red markers on the east wing, yellow on corridor B. Metrics panel shows: 4 violations, 2 critical. (15s)
5. Click "AI Diagnose" → EvacDiagnoser runs → plain-language explanation: east wing has only one exit serving 120 people, travel distance exceeds P118 limits, corridor B too narrow for occupant load. (15s)
6. Click "Propose Fix" → Redesigner runs → ranked list of proposals: add south exit to east wing, widen corridor B to 2.0m, add emergency door to room 12. Architect reads, evaluates, decides. (20s)
7. "This is how fire safety review should work — on the architect's desktop, during design, powered by AI reasoning on top of real Romanian regulations. The architect stays in control." (15s)

## Honest risks to manage

- **Plan parsing is the hardest technical piece.** If the vision LLM misreads walls/doors, validation is meaningless. Mitigation: ship with pre-validated example plans; make live upload a stretch goal.
- **Romanian regulation accuracy.** We implement core P118 rules, not the full regulatory code. Mitigation: be transparent about scope; position as early-stage decision support, not final compliance certification.
- **Judges may ask "why not just Pathfinder?"** Answer: Pathfinder is for specialists doing final review; we're for architects doing early iteration. Different user, different moment, different deployment model.
- **Liability framing.** Always position as decision-support for architects, not replacement for a licensed fire protection engineer. Judges respect appropriate humility on safety-critical domains.

## Key references teammates can cite

- Inspect Point, *Where AI Stands in Fire & Life Safety: A 2025 Snapshot* — fire safety field admits slow AI adoption
- Sparc FP, *The Role of AI in Fire Protection Engineering* — gap between AI promise and field-ready tools
- DiffEvac paper (arXiv 2510.19623, Oct 2025) — traditional evacuation sim too slow for early design iteration
- ScienceDirect 2025 — Pathfinder/MassMotion require heavy specialist prep
- MarketsAndMarkets — fire protection market $85B → $118B by 2030
- AEC Hub 2025 — AI adoption in AEC, 46% of ConTech investment going to AI
- **Romanian P118 norms** — national fire safety regulations for building design

---

*Send this to teammates. Each of them can feed it to their Claude/AI agent with: "Here's what we're building. Help me with [my specific piece — GUI, LLM prompts, validation logic, demo deck, etc.]." The brief has enough context for any agent to give grounded, consistent help on any slice of the project.*
