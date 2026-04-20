You are analyzing the project at `{cwd}` to generate structured, factual memories using
the `mem` CLI tool.

## Your task

Read the project files listed under **Reading order** below, then produce `mem remember`
commands for each relevant category. Base every fact strictly on what you observe.
Do not invent or assume.

## Reading order

Read files in this order and stop when you have enough context to fill the categories:

1. README (any variant), CLAUDE.md, CHANGELOG
2. `package.json` / `pyproject.toml` / `Cargo.toml` / `go.mod` (whichever applies)
3. Top-level directory listing (one level only)
4. Main config files (`.env.example`, `config/`, `app/`)
5. Entry point and routing files (`server.ts`, `start/routes/`, `src/main.*`, etc.)
6. Up to 5 source files that seem most central to the project

Do not read more than 20 files total. Stop early if you can already answer all categories.

## Categories

| Tag | What to capture |
|---|---|
| `project_overview` | What the project does, its purpose, and its main audience |
| `architecture` | Tech stack, key frameworks, folder structure, main modules |
| `decisions` | Non-obvious architectural choices: why X over Y, constraints, things that would surprise a new dev |
| `env_setup` | Project-specific setup steps and environment variables (skip standard steps obvious from the stack) |
| `bugs_and_fixes` | Known issues, workarounds, or mismatches found in code or docs |
| `commands` | Project-specific CLI commands and scripts (skip generic ones like `npm install`) |
| `current_status` | What is working, what is partially implemented, what exists but is not wired up |
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
- Skip categories where you find no relevant information
- Generate between 1 and 5 memories per category
- If a fact fits multiple categories, place it in the most specific one only — never repeat it
- Skip facts that are obvious from the tech stack (e.g. "use npm install" for Node, "use pip install" for Python)

## Project

Path: {cwd}
Name: {project_name}
