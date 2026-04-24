# Hackathon Project Brief: Fire Safety Evacuation Copilot

## Context

We're competing in the "App Dev with AI" division of a hackathon themed around **AI adoption in engineering — tools to transformation**. The brief emphasizes that AI adoption is a mindset and operating-model change, not just tool usage, and challenges teams to pick an engineering field where AI adoption is lacking and build something that genuinely shifts how work gets done.

An example that fit the theme well: for architecture engineering, a tool that optimizes an existing house floor plan and renders a realistic visualizer. That's the shape we're copying — upload a domain artifact, AI does the hard intellectual work, produce a compelling visual output.

## What we're building

**An AI-native fire safety and evacuation copilot for architects, running in the browser.**

An architect uploads a floor plan (image or PDF). The app:

1. Uses a vision LLM to parse the plan into structured data (rooms, doors, corridors, exits, walls)
2. Runs a classical agent-based evacuation simulation on that structure — animated dots flowing toward exits, with a fire that spreads and blocks paths over time
3. Reports metrics: evacuation time, congestion hotspots, code violations (travel distance, dead-end corridors, exit capacity)
4. Uses an LLM to diagnose the bottlenecks in plain language and propose specific plan modifications
5. Applies the fix and re-runs the simulation, showing before/after

The demo moment: watch people pile up at a bottleneck → click "AI redesign" → watch the AI add an exit → re-run → everyone escapes in half the time.

## Why this field and why this problem

Fire safety engineering is a real, regulated discipline almost entirely untouched by modern AI tooling. Academic papers from 2025 explicitly call out the gap: existing tools (Pathfinder, MassMotion, FDS) are desktop-based, expensive, require a trained specialist, and are too slow for rapid design iteration. Architects get fire safety feedback weeks later from outsourced consultants, so they don't iterate on it during design — they just hope the plan passes review.

Our wedge: put that feedback in the architect's browser, during design, in seconds. We don't compete with Pathfinder for the final specialist review. We own the 50 earlier design iterations that never get checked today.

## Positioning for judges

**Theme fit** — Fire safety is a genuinely underserved engineering domain (evidence: Inspect Point 2025 industry report, SFPE AI Summit 2025 at UC Berkeley, multiple 2025 academic papers). Our app changes *how* architects work, not just which tool they use — that's the "tools to transformation" thesis.

**Market** — $75B+ global fire protection market, $12B AEC software market, 46% of Q1 2025 construction tech investment going to AI. Every commercial building on earth requires fire egress review, so the use case is mandatory, not optional.

**Differentiation** — Pathfinder and peers target fire protection engineers, on desktop, with trained modelers, using clean BIM inputs, producing simulation reports. We target architects, in the browser, with zero training, from messy sketches/images, producing diagnosis + proposed fixes + re-run comparisons. The AI reasoning layer on top of classical simulation is the real novelty — no competitor does this.

**Pitch one-liner:** *"Every commercial building on earth has to prove people can escape it. Today that proof comes weeks later from a specialist. We give it to the architect in seconds, in the browser, while they're still drawing."*

## Technical architecture

**AI does:** floor plan parsing (vision LLM → JSON), diagnosis of simulation results (text LLM), redesign proposal (text LLM → modified JSON).

**Classical algorithms do:** the evacuation simulation itself — grid-based A* pathfinding with multiple agents, simple congestion rules at doorways (~1.3 persons/sec per meter of door width), expanding-radius fire/smoke that blocks cells over time. Roughly 200 lines of code.

**Stack:**
- Frontend: HTML + Canvas or SVG, vanilla JS or React. `p5.js` optional for the animation.
- Pathfinding: `pathfinding.js` npm package or write A* directly.
- LLM: Claude or OpenAI API with vision input, called client-side.
- Hosting: Vercel or Netlify, all client-side except LLM API calls.
- No backend server required.

**Data flow:**
```
[Floor plan image]
    → Vision LLM (parse to JSON: rooms, doors, exits, walls)
    → Grid conversion (walkable/wall cells)
    → Place agents by occupant density rules
    → Run simulation loop (A* + congestion + spreading fire)
    → Collect metrics (evac time, hotspots, unreached agents)
    → Text LLM (diagnose + propose fixes)
    → Modify JSON per LLM suggestion
    → Re-run simulation
    → Show before/after visuals
```

## Scope — what we're building vs. cutting

**Must ship:**
- 2–3 pre-parsed example floor plans (hardcoded as JSON fallback in case live parsing fails)
- Working 2D top-down animated simulation with agents, exits, and spreading fire
- Live metrics side panel (evac time, % escaped, congestion)
- "AI diagnose" button that returns plain-language issues
- "Apply fix & re-run" button showing the improved simulation
- Simple compliance check against 3–4 hardcoded NFPA-style rules (max travel distance, door width, dead-end corridor length, exit capacity)

**Stretch goals:**
- Live upload and parsing of arbitrary user floor plans
- Multiple fire origin scenarios
- Building type presets (office, school, restaurant, hospital) affecting occupant density
- 3D isometric view
- Exportable PDF compliance report

**Cut:**
- Multi-floor buildings (single floor only)
- Real CFD smoke simulation (use expanding radius instead)
- Full NFPA 101 code implementation (hardcode a handful of rules)
- User accounts, saving, sharing
- Any mobile support beyond what comes free from responsive web

## Demo script (90 seconds)

1. "Every commercial building must pass fire egress review. Architects today get this feedback weeks later from a specialist." (10s)
2. Load example plan — a real-looking office floor. (5s)
3. Click simulate → watch agents flow toward exits, fire starts in the kitchen, smoke spreads, watch a clear pile-up at a corridor bottleneck. (20s)
4. Metrics panel shows: 180s evac time, corridor B congested with 40 agents, 12 occupants didn't make it. (5s)
5. Click "AI Diagnose" → AI explains the east wing has only one exit serving 120 people, travel distance exceeds code, recommends adding a south exit + widening corridor B. (15s)
6. Click "Apply & Re-run" → AI modifies the plan, simulation re-runs, watch everyone escape in 95s, all code checks pass. (20s)
7. "This is how fire safety review should work — in the browser, during design, powered by AI reasoning on top of classical simulation." (15s)

## Honest risks to manage

- **Plan parsing is the hardest technical piece.** If the vision LLM misreads walls/doors, the whole sim is garbage. Mitigation: ship with pre-validated example plans; make live upload a stretch goal.
- **Judges may ask "why not just Pathfinder?"** Answer: Pathfinder is for specialists doing final review; we're for architects doing early iteration. Different user, different moment, different deployment model.
- **Liability framing.** Always position as decision-support for architects, not replacement for a licensed fire protection engineer. Judges respect appropriate humility on safety-critical domains.

## Key references teammates can cite

- Inspect Point, *Where AI Stands in Fire & Life Safety: A 2025 Snapshot* — fire safety field admits slow AI adoption
- Sparc FP, *The Role of AI in Fire Protection Engineering* — gap between AI promise and field-ready tools
- DiffEvac paper (arXiv 2510.19623, Oct 2025) — traditional evacuation sim too slow for early design iteration
- ScienceDirect 2025 — Pathfinder/MassMotion require heavy specialist prep
- MarketsAndMarkets — fire protection market $85B → $118B by 2030
- AEC Hub 2025 — AI adoption in AEC, 46% of ConTech investment going to AI

---

*Send this to teammates. Each of them can feed it to their Claude/AI agent with: "Here's what we're building. Help me with [my specific piece — frontend, LLM prompts, simulation code, demo deck, etc.]." The brief has enough context for any agent to give grounded, consistent help on any slice of the project.*
