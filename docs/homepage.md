# memcli.ai — Homepage Content

> Design reference for the memcli.ai landing page.
> Brand gradient: **Pink `#E93A7D` → Coral `#F25C5C` → Orange `#F98C2B` → Yellow `#F7B500`**
> Background: near-black `#0D0D0D`. Text: `#F0F0F0`. Accents use the gradient on key words, CTAs, and borders.

---

## [SECTION] Nav

```
mem-cli          Docs    GitHub    ▶ Get started
```

- Logo: ASCII mark (from `docs/logoascii.txt`) rendered in the brand gradient, followed by `mem-cli` in white
- Links: Docs, GitHub (icon)
- CTA button: `Get started` — filled, gradient border, dark background

---

## [SECTION] Hero

### Headline

> **Your AI agents forget everything.**
> **mem-cli remembers.**

### Subheadline

`mem-cli` is an open-source CLI that gives Claude Code and Codex two things they lose between sessions: **persistent project memory** and **real-time token visibility** — all local, all yours.

### CTA buttons

- Primary: `Install now` → anchor to #install
- Secondary: `View on GitHub` → github.com/your-org/mem-cli

### Hero visual

Terminal window showing:

```
$ mem remember "use postgres for all new services" --tag architecture
  ✔  Saved  a1c9c378  mem-cli  2026-04-27

$ mem recall
  ID        Content                                   Tags           Saved
  ──────────────────────────────────────────────────────────────────────────
  a1c9c378  use postgres for all new services         architecture   today
  e52d0eef  python 3.11+ required                     deps           today
  f9a30012  run tests: pytest tests/ -v               commands       today
```

---

## [SECTION] Problem / Why

**Heading:** Every agent session starts from zero.

**Body:**
You spend a session explaining your stack, your decisions, your constraints. The agent figures things out. Then it stops — and forgets all of it. Next session, you start over.

And there's no easy way to know how many tokens you've spent across sessions, across projects, or across agents.

**Three-column cards:**

| | | |
|---|---|---|
| **No memory** | **No visibility** | **No control** |
| Agents forget project context the moment a session ends. Every new session is a blank slate. | You have no clear picture of token spend across Claude, Codex, or multiple projects. | Your agent's context is a black box. You can't search it, edit it, or hand it to another tool. |

---

## [SECTION] Features

**Heading:** Everything your agent needs to stay useful across sessions.

### Feature 1 — Project Memory

Store and retrieve facts scoped to each project directory. Works from the terminal or directly through MCP tools called by the agent itself.

```bash
mem remember "do not use black, use ruff instead" -t style
mem recall --tag style
```

No database. No cloud. Everything is local JSONL under `~/.mem-cli/`.

---

### Feature 2 — MCP Server

`mem serve` launches a local MCP server over stdio. Register it once in your Claude Code settings and the agent can read, write, and clean up its own memory — no shell access needed.

```json
{
  "mcpServers": {
    "mem": { "command": "mem", "args": ["serve"] }
  }
}
```

Tools available: `memory_recall`, `memory_remember`, `memory_forget`, `memory_projects`, `monitor_snapshot`, `monitor_status`, `monitor_start`, `monitor_stop`.

---

### Feature 3 — Token Monitor & Live Dashboard

A background process captures token events from Claude and Codex as they happen. `mem dashboard` gives you a live terminal view — input tokens, output tokens, average tokens/minute, per agent.

```bash
mem start      # start the monitor
mem dashboard  # open the live view
```

---

### Feature 4 — Auto Memory Init

Point `mem init` at any project and it runs Claude or Codex against the codebase to generate a structured set of memories automatically — architecture, decisions, environment setup, known bugs, next steps.

```bash
mem init --agent claude
# → outputs ready-to-run `mem remember` commands organized by category
# → pipe to bash or review first
```

---

### Feature 5 — Semantic Search

Search your memories by meaning, not just keywords. Built on sentence-transformers, runs entirely on your machine.

```bash
mem recall "database choice"
# → returns memories about postgres, sqlite decisions, storage rationale
```

---

### Feature 6 — AI Memory Compression

`mem compress` calls your agent to merge and deduplicate redundant memories, keeping your context tight and relevant.

```bash
mem compress
# → agent merges 14 memories into 6 without losing information
```

---

## [SECTION] How It Works

**Heading:** One setup. Memory that survives every session.

```
1. Register mem serve in your agent settings
        ↓
2. Agent calls memory_recall(cwd) on first turn
   → loads prior context from this project
        ↓
3. During the session, agent calls memory_remember(...)
   → stores facts that should persist
        ↓
4. Next session — memory_recall returns everything
   → no explaining your stack again
```

**Visual:** Vertical flow diagram with the four steps. Gradient accent on arrows and step numbers.

---

## [SECTION] Install

**Heading:** Up in under a minute.

```bash
# 1. Clone
git clone https://github.com/your-org/mem-cli.git
cd mem-cli

# 2. Install
pip install -e .

# 3. Verify
mem --version

# 4. Register the MCP server in ~/.claude/settings.json
# (see Docs for the full settings block)

# 5. Start using memory
mem remember "your first project fact"
mem recall
```

**Requirements badge strip:** Python 3.11+  ·  macOS / Linux / Windows  ·  MIT License  ·  Local only

---

## [SECTION] Compatibility

**Heading:** Works with the agents you already use.

| Agent | Memory via MCP | Token tracking | Auto-init |
|---|---|---|---|
| **Claude Code** | ✔ | ✔ via hook | ✔ |
| **Codex CLI** | ✔ | ✔ via watcher | ✔ |
| **Any MCP client** | ✔ | — | — |

---

## [SECTION] Testimonials / Social Proof

_(placeholder — fill with real quotes once available)_

> "I stopped re-explaining my architecture every session."
> — Early tester

> "The token dashboard alone was worth the install."
> — Early tester

---

## [SECTION] Open Source

**Heading:** Local. Open. Yours.

mem-cli is MIT-licensed and runs entirely on your machine. No accounts, no telemetry, no data leaving your environment. Memory is stored as plain JSONL files you can read, edit, or delete at any time.

**Links:** View on GitHub · Read the docs · Report an issue

---

## [SECTION] Footer

```
mem-cli                   Docs    GitHub    Changelog    Roadmap
MIT License · Built for AI-native workflows · memcli.ai
```

---

## Brand Notes for Implementation

| Token | Value | Usage |
|---|---|---|
| Pink | `#E93A7D` | Primary CTAs, logo left edge, active nav |
| Coral | `#F25C5C` | Gradient midpoint, warning states |
| Orange | `#F98C2B` | Gradient midpoint, hover states |
| Yellow | `#F7B500` | Logo right edge, highlighted text, badges |
| Background | `#0D0D0D` | Page background |
| Surface | `#161616` | Cards, terminal windows |
| Border | `#2A2A2A` | Card borders, dividers |
| Text | `#F0F0F0` | Body copy |
| Dim text | `#888888` | Captions, secondary labels |

**Gradient (CSS):**
```css
background: linear-gradient(90deg, #E93A7D, #F25C5C, #F98C2B, #F7B500);
```

**Terminal window component:**
- Background: `#161616`
- Top bar: `#1E1E1E` with three dots (red/yellow/green)
- Font: monospace, 13–14px
- Text: `#F0F0F0`
- Prompt `$`: gradient color

**Typography:**
- Headings: sans-serif, bold, white
- Key words in headings: gradient via `background-clip: text`
- Body: 16–18px, `#C0C0C0`, 1.6 line-height
- Code / terminal: `JetBrains Mono`, `Fira Code`, or `IBM Plex Mono`
