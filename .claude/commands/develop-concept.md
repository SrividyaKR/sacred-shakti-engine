---
description: Develop and debate video concepts for a deity with the Claude Code subagents (research, director, three critics). Usage: /develop-concept <deity id>
---

Develop concepts for the deity `$ARGUMENTS` using the project's subagents. You are the orchestrator; subagents cannot call each other.

1. If `research/$ARGUMENTS.md` does not exist (or the user asked for more research), launch the **deity-researcher** agent for `$ARGUMENTS` and wait.
2. Launch **concept-director** in Propose mode for `$ARGUMENTS` (6 concepts).
3. Launch **virality-critic**, **authenticity-critic** and **feasibility-critic** in parallel, each given all the concepts and the deity id.
4. Run `.venv/bin/python scripts/check_storyboard.py --character $ARGUMENTS <file>` for each concept (save them under concepts/$ARGUMENTS/proposals/ first).
5. Pick the top two by authenticity (>= 8), then virality, with feasibility as a flagged risk; send each to **concept-director** in Revise mode with all feedback and the guard output. Repeat steps 3-5 at most twice, stopping early when nothing improves.
6. Present the finalists to the user with scores, risks and the compiled prompt (`--show-prompt`). Do not render. The human director chooses; rendering costs credits and needs their go-ahead.
