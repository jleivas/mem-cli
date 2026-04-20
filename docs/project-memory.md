# Project Memory

Project memory is the core feature of `mem-cli`. It lets you store, search, and retrieve
notes and facts scoped to a specific project directory. Each memory is automatically
associated with the current working directory, so running `mem recall` from any project
folder shows only what is relevant to that project.

## How it works

When you run any memory command, `mem` resolves the active project from the working
directory using the following priority:

1. `--cwd` flag (explicit override, mainly for scripts and hooks)
2. `$PWD` environment variable
3. `os.getcwd()` at runtime

The resolved path is used as the project key. Memories are stored locally under
`~/.mem-cli/projects/<project-slug>/memories.jsonl` — one JSON object per line.
No database, no remote service.

## Storage layout

```
~/.mem-cli/
└── projects/
    └── <project-name>-<sha256[:12]>/
        ├── meta.json        # project path and display name
        └── memories.jsonl   # one memory per line
```

Each project directory is named after the last component of the project path plus a
short hash of the full path. This keeps directory names readable while guaranteeing
uniqueness even when two projects share the same folder name.

## Commands

### `mem remember`

Store a new memory for the current project.

```bash
mem remember "<content>"
mem remember "<content>" --tag <tag>        # add one tag
mem remember "<content>" -t <tag> -t <tag>  # multiple tags
```

**Examples:**

```bash
mem remember "use typer for all CLI commands"
mem remember "python 3.11+ required" --tag deps
mem remember "do not use black, use ruff instead" -t style -t linting
```

**Output:** confirms the memory ID, project name, content, and tags.

---

### `mem recall`

List memories for the current project, newest first.

```bash
mem recall
mem recall "<query>"   # filter by substring (case-insensitive)
```

**Examples:**

```bash
mem recall
mem recall typer
mem recall "3.11"
```

**Output:** table with ID, content, tags, and save date. Shows a message when there are
no memories or no matches for the query.

---

### `mem forget`

Delete a memory by its ID.

```bash
mem forget <id>
```

**Examples:**

```bash
mem forget e52d0eef
```

**Output:** confirms deletion, or exits with code `1` if the ID is not found in the
current project.

---

### `mem projects`

List all projects that have stored memories.

```bash
mem projects
```

**Output:** table with project name, full path, and memory count, sorted alphabetically.

---

## Using `--cwd` from scripts and hooks

All memory commands accept a hidden `--cwd` flag that overrides the project resolution.
This is intended for hooks and automation where the working directory cannot be relied on.

```bash
mem remember "session ended cleanly" --cwd /path/to/project
mem recall --cwd /path/to/project
mem forget <id> --cwd /path/to/project
```

## Memory format

Each line in `memories.jsonl` is a self-contained JSON object:

```jsonl
{"id":"e52d0eef","content":"use typer for CLI","project":"/projects/mem-cli","project_name":"mem-cli","timestamp":"2026-04-20T20:48:00+00:00","tags":[]}
{"id":"a1c9c378","content":"python 3.11+ required","project":"/projects/mem-cli","project_name":"mem-cli","timestamp":"2026-04-20T20:48:01+00:00","tags":["deps"]}
```

| Field | Type | Description |
|---|---|---|
| `id` | string | 8-character hex identifier |
| `content` | string | the memory text |
| `project` | string | absolute path of the project directory |
| `project_name` | string | last component of the project path (display only) |
| `timestamp` | ISO 8601 | UTC timestamp of when the memory was saved |
| `tags` | string[] | optional labels |

## Roadmap

Project memory is MVP 3 in the [roadmap](roadmap.md). The next planned stages are:

- **MVP 4** — expose memory through a local MCP server so agents can read and write
  memories directly during a session without using the CLI manually.
- **MVP 5** — packaging and distribution improvements.
