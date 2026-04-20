You are analyzing the project at `{cwd}` to generate structured, factual memories using
the `mem` CLI tool.

## Your task

Explore the project thoroughly — read the main configuration files, documentation, source
code structure, and any relevant scripts — then produce `mem remember` commands for each
category below. Base every fact strictly on what you observe in the project. Do not invent
or assume.

## Categories

| Tag | What to capture |
|---|---|
| `project_overview` | What the project does, its purpose, and its main audience |
| `architecture` | Tech stack, key frameworks, folder structure, main modules |
| `decisions` | Explicit choices made: why X over Y, trade-offs, constraints |
| `env_setup` | How to install dependencies, configure environment variables, and run locally |
| `bugs_and_fixes` | Known issues, workarounds, recurring problems found in code or docs |
| `commands` | Important CLI commands, scripts, make targets, and shortcuts |
| `current_status` | What is working, what is in progress, what is incomplete |
| `next_steps` | Open tasks, TODOs, planned features found in docs or code comments |

## Output format

Output ONLY `mem remember` commands — one per line — with no explanation, headers,
or commentary before or after.

```
mem remember "<fact>" --tag <category>
```

Rules:
- One fact per line, nothing else
- Each fact must be a concrete, self-contained statement (under 120 characters)
- Use only the tags from the table above
- Skip categories where you find no relevant information in the project
- Generate between 1 and 5 memories per category
- Do not repeat the same fact across categories

## Project

Path: {cwd}
Name: {project_name}

Start by reading: README, CLAUDE.md, pyproject.toml / package.json / Cargo.toml /
go.mod (whichever applies), then explore the top-level directory structure and main
source folders.
