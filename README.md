# SpinDoctor Qwerty Companion

An [Agent Plugins 1.0.0](https://agent-plugins.org) package that runs the **SpinDoctor 3.1.2 quantum-circuit simulator** on your
computer through MCP: `q.*` circuit scripts (1-298 logical qubits), the 241 built-in presets, folders of command files
(`q.folder`), and theory tests from a file, pasted text or the chat, each with TXT, PDF, JSON and CSV reports. It brings a local MCP
server (6 tools), a skill, and an optional Windows launcher - the "companion" - that you build from source.

## What this is, and what it is not

- **Not a Midjourney plugin.** It sits in the Midjourney-companion slot of the SpinDoctor Qwerty set, but Midjourney has no plugin,
  extension or MCP interface and no public API (only an "Enterprise API" it says it is investigating). This package does not
  connect to Midjourney, does not use a Midjourney account, does not make images, and nothing in it talks to the network.
- **What it is:** a plugin for AI tools that load Agent Plugins packages or MCP servers (for example Kiro powers, or any MCP client
  you point at the server). The simulator runs locally in Python.
- **The companion** (`SpinDoctor.Qwerty.Companion.exe`) is a small native launcher, not a second simulator. The Agent Plugins format
  lets a server's `command` be one executable name with no arguments, so `py -3` (how Python is usually started on Windows) cannot
  be written there, and many Windows PCs have no `python3`. The companion finds a working Python 3 and hands the MCP conversation,
  byte for byte, to the bundled Python server. You only need it on Windows, and only if `python3` does not work there.

> **Honest limits.** SpinDoctor is a classical FP64 simulator. It is not a quantum computer, does not connect to quantum hardware,
> and gives no quantum speed-up or advantage. One entangled group is limited to 59 qubits and dense groups are limited by memory
> (2^n x 16 bytes). Registers wider than 29 qubits sample in basis Z only. Histograms are seeded Born samples.

Version 1.1.0 - engine 1.1.0 (SpinDoctor 3.1.2 parity) - Python 3.8+, standard library only - no network, no account, no keys.
Tested with a stand-in host, not a real one; see [Testing](#testing).

## Install

1. Get the folder: `git clone https://github.com/LKVexa/spindoctor-qwerty-midjourney-companion` (or download the ZIP).
2. Load it in your tool as an Agent Plugins package (for example Kiro: *Import power from a folder* / *from GitHub*), or add the MCP
   server by hand, for example:

```json
{ "mcpServers": { "spindoctor-qwerty": { "command": "python3",
  "args": ["/path/to/spindoctor-qwerty-midjourney-companion/skills/spindoctor-qwerty/scripts/spindoctor_mcp.py"] } } }
```

As shipped, `mcp.json` starts `python3 ${PLUGIN_ROOT}/skills/spindoctor-qwerty/scripts/spindoctor_mcp.py` - no build step.

### Windows: build and use the companion (optional)

```bat
py tools\build_companion.py --use
```

This compiles `companion-src\SpinDoctor.Qwerty.Companion.cs` with the C# compiler that ships with .NET Framework 4.x
(`%WINDIR%\Microsoft.NET\Framework64\v4.0.30319\csc.exe` - nothing to download), writes `server\SpinDoctor.Qwerty.Companion.exe`
and `server\BUILD_INFO.txt` (compiler, SHA-256), and points `mcp.json` at `./server/SpinDoctor.Qwerty.Companion.exe`. Reload the
plugin in your tool. `py tools\build_companion.py --unuse` switches back to `python3`. By hand:

```bat
%WINDIR%\Microsoft.NET\Framework64\v4.0.30319\csc.exe /nologo /optimize+ /target:exe /out:server\SpinDoctor.Qwerty.Companion.exe companion-src\SpinDoctor.Qwerty.Companion.cs
```

The companion uses `SPINDOCTOR_PYTHON` if set (a command, arguments or a quoted path allowed: `py -3`,
`"C:\Program Files\Python312\python.exe"`), otherwise the first of `py -3`, `python`, `python3` that really runs Python 3 (so the
Windows Store "python" alias is skipped). `SpinDoctor.Qwerty.Companion.exe --which-python` shows what it picked; `--version` prints
the version. With no Python it answers every request with an error that says what to install. Builds are repeatable from the
source; byte-identical only with Roslyn's `/deterministic` (used automatically when `csc` on PATH is Roslyn) - the .NET Framework
compiler and Mono stamp a new module id each time. This repository never ships the .exe; build it yourself so you know what runs.

## What's in the repo

| Path | What it is |
|---|---|
| `plugin.json` | Agent Plugins manifest: name `spindoctor-qwerty-companion`, version, description, author, keywords, license |
| `mcp.json` | MCP server `spindoctor-qwerty-companion` (python3 + bundled server; or the companion after `--use`) |
| `skills/spindoctor-qwerty/` | Skill (`SKILL.md`), the bundled engine (`spindoctor/`), CLI and MCP server (`scripts/`), examples, LICENSE |
| `companion-src/SpinDoctor.Qwerty.Companion.cs` | Companion source (C# 5, .NET Framework 4.x, no packages) |
| `tools/build_companion.py` | Builds the companion into `server/`, `--use` / `--unuse` rewire `mcp.json` |
| `server/` | Empty except a README until you build |
| `FUNCTIONS.md` | The full function table with a runnable example for every command |
| `tests/` | Stand-in Agent Plugins host and host check, shared end-to-end suite, reference outputs |

## Using it

- Ask in plain language: "show the SpinDoctor functions", "run a 3-qubit GHZ circuit", "test the Bell state theory we discussed".
- Tools: `spindoctor_functions`, `spindoctor_run_script`, `spindoctor_run_preset`, `spindoctor_list_presets`, `spindoctor_report`,
  `spindoctor_test_theory`.
- The server runs with the plugin folder as its working directory, so give **absolute paths** for files and folders. Reports and
  state go to `~/spindoctor-workspace` unless a call passes `workspace`; nothing is written into the plugin folder.
- Without the tools, the skill tells the AI to run the same commands with `scripts/spindoctor_cli.py` from the skill folder.

## SpinDoctor Qwerty - plugin tools

| Function | What it does | Command to type |
|---|---|---|
| Function table (spindoctor_functions) | Show this table in chat | Ask: "show the SpinDoctor functions" |
| Run a script (spindoctor_run_script) | Run any q.* lines above; returns results + TXT/JSON/CSV/PDF report paths | Ask: "run q.circuit new bell 2 / q.circuit add h 0 / ..." |
| Run a preset (spindoctor_run_preset) | Run qc-001..qc-241 with overrides | Ask: "run preset qc-067 with shots=64" |
| List presets (spindoctor_list_presets) | Search the 241 presets | Ask: "list presets about Grover" |
| Read a report (spindoctor_report) | List/read TXT reports (PDF/JSON paths alongside) | Ask: "show the newest SpinDoctor report" |
| Test a theory from a file (spindoctor_test_theory source=file) | Read a .txt/.md/.pdf/.py/.json/.csv/.q attachment, then hypothesis -> prediction -> q.* script -> run -> verdict + TXT/PDF theory report | Ask: "test the theory in C:/notes/theory.md" (the host must pass the file path/content) |
| Test a theory from text (spindoctor_test_theory source=text) | Same pipeline for pasted text | Ask: "test this theory: a Hadamard on \|0> gives 50/50" |
| Test the theory we discussed (spindoctor_test_theory source=chat) | The AI summarises the theory from the conversation (claims, assumptions, variables, prediction), you confirm, then it is tested; quoted excerpts go in the report under 'Source: chat history'. An exported chat transcript (.txt/.md/.json/.html) also works | Ask: "test the theory we discussed" or "test the theory in my exported chat C:/chats/conversation.json" |

Every command family is listed with a runnable example in **[FUNCTIONS.md](FUNCTIONS.md)** (the exact table the tool shows):
circuits (`q.circuit`, including 298-qubit wide registers and the `mcx7` gate), queries (`q.query`), the tranche register
(`q.tranche`), the procedural grid, presets and sequences, resource planning, math calculators, physics models, lessons, noise, error
correction, compilation, algorithms, inputs/folders/history (`q.input`, `q.folder`, `q.history`) and the cartridge commands.

## Theory testing

`spindoctor_test_theory` turns a claim into a test: hypothesis -> measurable prediction -> `q.*` script -> run -> compare -> a TXT +
JSON + PDF **theory test report** with the hypothesis, script, raw results, verdict (*supported*, *not supported* or *inconclusive*)
and limits.

- **From a file:** .txt, .md, .pdf, .py, .json, .csv or .q. Give the file's absolute path on your computer (the server runs in the plugin folder), or paste the text.
- **From pasted text.**
- **From the chat history:** say *"test the theory we discussed"*. The model writes a short summary (claims, assumptions, variables,
  measurable prediction), shows it to you to confirm or correct, then passes it with optional quoted excerpts; the report records them
  under *Source: chat history*. Exported chat transcripts (.txt/.md/.json/.html from ChatGPT, Claude and others) also work.
- The plugin cannot read your conversation or attachments by itself: only the model sees them, and very long conversations may already
  be truncated by the context window.

Sample theory files and chat transcripts are in `skills/spindoctor-qwerty/examples/theory/`. The two sample
PDFs are stored as text; run `python3 skills/spindoctor-qwerty/examples/theory/make_sample_pdfs.py` to
recreate them.

## Folder ingestion (`q.folder`)

`q.folder run path="<folder>"` runs every supported file at the top level of a folder (.txt, .csv, .json, .qasm, .qasm2, .circuit,
.pdf) in ordinal name order: 1-128 supported files, at most 4 MiB per file, 1-128 commands per file and 4096 characters per command,
strict UTF-8. Other files (for example .md) are skipped and listed. The first failing file stops the job.


## Testing

| Test | Command |
|---|---|
| Stand-in host check (this folder) | `python3 tests/companion_standin_host.py` |
| Same, installing from GitHub | `python3 tests/companion_standin_host.py --source https://github.com/LKVexa/spindoctor-qwerty-midjourney-companion` |
| End-to-end suite only | `python3 tests/e2e_mcp.py --server python3 skills/spindoctor-qwerty/scripts/spindoctor_mcp.py --examples skills/spindoctor-qwerty/examples/theory` |

**Stand-in host, no Midjourney.** There is no Midjourney host to test in (see above). `tests/companion_standin_host.py` plays a
generic Agent Plugins 1.0.0 client: it validates the manifest, skill and mcp.json by the spec (first rejecting ten deliberately
broken variants, including `py -3` as a command), installs the plugin into a throwaway home, starts the server exactly as configured
and calls all 6 tools (function table, Bell, qc-001, GHZ presets, reports, a 298-qubit `mcx7` circuit, a theory from a file and from
the chat: verdict *supported*, PDF written). Then it builds the companion from source inside the installed copy, rewires mcp.json,
runs the same calls through it, checks its tool list equals the Python server's, checks `--which-python`, a quoted
`SPINDOCTOR_PYTHON` with arguments, the no-Python error, `--unuse`, a rebuild, and runs the shared end-to-end suite through it. On
this Linux test machine the companion was compiled with Mono's `mcs` (C# 5, .NET 4.5 profile) and run under Mono. **Not tested:**
Windows itself, the .NET Framework `csc.exe` build, any real host's UI or installer, a real model choosing the tools, macOS.
Results: [E2E_RESULTS.md](E2E_RESULTS.md).

## Author and license

Author: **RUSSELL PHILIP SMITHSON** <russellsmithson77@outlook.com>

Copyright (C) 2026 RUSSELL PHILIP SMITHSON. Licensed under the GNU General Public License v3.0 or later (`GPL-3.0-or-later`): see
[LICENSE](LICENSE), [NOTICE](NOTICE) and [COPYRIGHT](COPYRIGHT). Not affiliated with Midjourney, Inc.
