# ZeroTouch SRE — Demo Script (2:50)

## Quick Reference Card — What to Say & Click

### [0:00-0:15] HOOK
**Screen:** Landing page already loaded
**Say:** "So when a production alert fires, engineers spend 15-20 minutes just figuring out what happened. I built an agent that does all of that in about 5 seconds. Let me show you."

### [0:15-1:00] LIVE DEMO
**Screen:** Scroll to Incident Workbench
**Say:** "This is deployed live on Cloud Run — not localhost."
**Click:** "Run checkout scenario"
**While loading (~4s):** "The agent is receiving the alert, pulling telemetry from Dynatrace, running root-cause analysis through Gemini, checking safety policies..."
**Results appear:** "Done. 4 seconds."
**Point at:** Root cause (CPU saturation), 3 actions (scale, rollback, open channel), telemetry_mode (live-dynatrace-openpipeline)
**Say:** "It's not just reading from Dynatrace — it's writing audit events back."

### [1:00-1:35] DYNATRACE
**Scroll to:** "Connect your Dynatrace" panel
**Say:** "This lets anyone — including judges — plug in their own Dynatrace URL and token. The agent pushes events into YOUR tenant and pulls logs from YOUR services. Bidirectional. We've already pushed 18 events across 3 incidents."

### [1:35-2:05] SAFETY
**Point at:** Actions and simulation mode
**Say:** "An autonomous agent touching production is scary. So every action goes through a policy gate — only allowlisted operations. Everything runs in simulation mode, no live writes, destructive actions require human approval. It also auto-generates a post-mortem, runbook, and execution trace. Useful, not dangerous."

### [2:05-2:25] ARCHITECTURE (QUICK)
**Scroll to:** "What happens on every run"
**Say:** "6-step loop: perceive, retrieve, reason, plan, execute, synthesize. FastAPI on Cloud Run, Dynatrace for telemetry, Gemini for reasoning."

### [2:25-2:50] CLOSE
**Say:** "What takes 15-20 minutes of scrambling, this does in 5 seconds. It's live on Cloud Run right now. The Dynatrace integration is real and bidirectional. You can connect your own Dynatrace to test it yourself. ZeroTouch SRE. Thanks for watching."

---

## Pre-Flight
```
1. Open: https://zerotouch-sre-971465910048.us-central1.run.app
2. Browser zoom: 110-125%
3. One tab only, bookmarks hidden, notifications off
4. Mic tested, script on second monitor
5. Practice 2-3x, record 3 takes, pick best
```

## Demo URL
```
https://zerotouch-sre-971465910048.us-central1.run.app
```
