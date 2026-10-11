# E2E results - spindoctor-qwerty-midjourney-companion 1.1.0

Host: **stand-in Agent Plugins 1.0.0 client** (`tests/companion_standin_host.py`). There is no Midjourney host: Midjourney has no
plugin, extension or MCP interface. The stand-in validates the manifest, skill and mcp.json by the spec (and first rejects ten broken
variants), installs the plugin into a throwaway home, starts its MCP server exactly as configured and speaks MCP to it - first as
shipped (`python3`), then through the companion launcher built from `companion-src/` by `tools/build_companion.py --use`. Companion
build on this machine: Mono `mcs` (C# 5, .NET 4.5 profile); run under Mono JIT compiler version 6.12.0.199 (tarball Thu Apr  3 15:13:01 UTC 2025). Python 3.13.5.

Not tested: Windows and its .NET Framework `csc.exe` build, any real host's UI or installer, a real model choosing the tools, macOS.

## Host check: 41/41

| Result | Check |
|---|---|
| PASS | plugin.json: version 1.1.0, GPL-3.0-or-later, author name/email, homepage/repository, honest description (not a Midjourney integration) |
| PASS | mcp.json as shipped starts python3 with the bundled server (the .exe is not in the repo) |
| PASS | every .py/.cs file has a GPL-3.0-or-later SPDX header (27 files) |
| PASS | no binaries tracked in git (no .exe/.dll/.pdb) |
| PASS | no symlinks in the package (containment rule) |
| PASS | SKILL.md: guardrail, server name, absolute-path rule, no-Midjourney note, no host variables |
| PASS | shell fallback: every CLI command in SKILL.md runs as written from the skill folder (6 commands) |
| PASS | stand-in loader refuses 4 bad manifests (uppercase name, extra author field, keywords not a list, unknown $schema) and skips 6 bad servers ('py -3' as command, ../ command, placeholder in command, env PLUGIN_ROOT, absolute cwd, unknown field) |
| PASS | install from a folder: manifest valid, no loader warnings |
| PASS | discovered 1 skill (spindoctor-qwerty) and 1 stdio server (spindoctor-qwerty-companion/spindoctor-qwerty-companion) |
| PASS | python3 server (as shipped): server started as configured, MCP initialize ok, cwd = plugin root |
| PASS | python3 server (as shipped): tools/list returns the 6 SpinDoctor tools (spindoctor_functions marked read-only) |
| PASS | python3 server (as shipped): spindoctor_functions -> the Markdown function table |
| PASS | python3 server (as shipped): Bell circuit ok, reports under ~/spindoctor-workspace |
| PASS | python3 server (as shipped): run_preset qc-001 |
| PASS | python3 server (as shipped): list_presets ghz |
| PASS | python3 server (as shipped): report lists the newest reports |
| PASS | python3 server (as shipped): 298-qubit wide register with mcx7 (3.1.2 parity) |
| PASS | python3 server (as shipped): theory extract from an absolute path |
| PASS | python3 server (as shipped): theory from the chat: supported, 2 excerpts, valid PDF |
| PASS | installed plugin folder unchanged by tool use (no __pycache__, reports outside) |
| PASS | tools/build_companion.py --use builds server/SpinDoctor.Qwerty.Companion.exe from companion-src/ and points mcp.json at ./server/SpinDoctor.Qwerty.Companion.exe |
| PASS | server/BUILD_INFO.txt records compiler and the exe's SHA-256 |
| PASS | rewired mcp.json is still valid Agent Plugins (plugin-relative ./ command, no args) |
| PASS | companion launcher: server started as configured, MCP initialize ok, cwd = plugin root |
| PASS | companion launcher: tools/list returns the 6 SpinDoctor tools (spindoctor_functions marked read-only) |
| PASS | companion launcher: spindoctor_functions -> the Markdown function table |
| PASS | companion launcher: Bell circuit ok, reports under ~/spindoctor-workspace |
| PASS | companion launcher: run_preset qc-001 |
| PASS | companion launcher: list_presets ghz |
| PASS | companion launcher: report lists the newest reports |
| PASS | companion launcher: 298-qubit wide register with mcx7 (3.1.2 parity) |
| PASS | companion launcher: theory extract from an absolute path |
| PASS | companion launcher: theory from the chat: supported, 2 excerpts, valid PDF |
| PASS | companion's tools/list is identical to the Python server's (it relays, it cannot drift) |
| PASS | companion --version / --which-python: 'SpinDoctor Qwerty Companion 1.1.0', a Python 3 found by probing |
| PASS | SPINDOCTOR_PYTHON with a quoted path plus arguments is honoured (1.0 treated the whole value as a file name) |
| PASS | no Python: every request gets a JSON-RPC error that says Python 3.8+ is required (no hang, no crash) |
| PASS | build_companion.py --unuse restores the shipped mcp.json byte for byte |
| PASS | rebuild from the same source gives the same program (same size; byte-identical only with Roslyn /deterministic) |
| PASS | shared end-to-end suite through the companion launcher: SUMMARY 12/12 passed in 13.2s |

## Shared end-to-end suite through the companion launcher: 12/12

Started as `mono <installed plugin>/server/SpinDoctor.Qwerty.Companion.exe` (the launcher relays to the bundled Python server).

| Result | Check |
|---|---|
| PASS | initialize (server spindoctor-qwerty 1.1.0) |
| PASS | tools/list exposes the 6 tools |
| PASS | function table (Markdown, 19 sections, 298-qubit limits listed) |
| PASS | 241 presets listed |
| PASS | one script per command family (16 families, every table example) |
| PASS | 298-qubit circuit with mcx7 (prepared-factor-Born-Z) |
| PASS | q.folder on mixed .txt/.csv/.json/.qasm folder (+ .md skipped) |
| PASS | theory from a file -> supported, TXT+PDF report |
| PASS | theory from a chat summary + quoted excerpts -> supported |
| PASS | theory from an exported chat transcript -> supported |
| PASS | presets qc-001..qc-025 match the updated 3.1.2 reference (20 identical, 5 documented differences) |
| PASS | TXT+PDF reports valid (255 PDFs, 255 TXT twins) |

## Runs

- Pre-push: stand-in host check 41/41 (folder install, python3 server + companion built with Mono mcs and run under Mono), shared suite through the companion 12/12.
