# Changelog

## 1.1.0 - 2026-10-11

- Engine 1.1.0 at parity with the updated SpinDoctor 3.1.2: 1-298 logical qubits (59 per entangled factor), the `mcx7` gate,
  wide-register Born-Z sampling, `q.folder` with 3.1.2 semantics, CSV report copies and measurement-CSV fitting equations. All 241
  presets replayed. Tools `spindoctor_functions` (function table, marked read-only) and `spindoctor_test_theory`. 1.0 described
  SpinDoctor 3.0.3 and a 29-qubit cap.
- **Honest about what it is.** 1.0 called itself a "Midjourney-companion-style plugin". Midjourney has no plugin, extension or MCP
  interface (and no public API), so nothing here connects to Midjourney. The README and plugin.json now say plainly: an Agent
  Plugins 1.0.0 package for MCP hosts, with an optional Windows launcher - the "companion".
- **No committed .exe.** 1.0 shipped a prebuilt `server/SpinDoctor.Qwerty.Companion.exe` with no build record. 1.1.0 ships the C#
  source (`companion-src/`) and `tools/build_companion.py`, which builds it with the C# compiler that comes with .NET Framework 4.x
  on Windows (no downloads), Roslyn `csc`, or Mono's `mcs`, and writes `server/BUILD_INFO.txt` (compiler, SHA-256).
- **Works without building anything.** 1.0's mcp.json pointed at the .exe only, so the plugin had no working server on macOS or
  Linux. 1.1.0's mcp.json starts `python3` with the bundled server by default; `build_companion.py --use` switches it to the
  launcher (and `--unuse` back).
- **The companion is now a launcher, not a second implementation.** 1.0's exe re-implemented the MCP server in C# and kept its own
  copy of the tool list, which had drifted from the engine (no read-only marking, shorter schemas, 29-qubit wording). 1.1.0's exe
  finds Python and relays stdio byte for byte to the bundled engine's MCP server, so tools, schemas and results always match.
- **Finding Python on Windows.** 1.0 tried `python.exe`, `python3.exe`, `py.exe` and stopped at the first that *started* - the
  Windows Store "python" alias starts but runs nothing, which ended in an empty error. It also treated `SPINDOCTOR_PYTHON` as one file
  name, so `py -3` failed. 1.1.0 probes `py -3`, `python`, `python3` for a real Python 3 and accepts a command with arguments or a
  quoted path in `SPINDOCTOR_PYTHON`. `--which-python` shows the choice.
- **No Python, clear answer.** 1.1.0 answers every request with a JSON-RPC error saying Python 3.8+ is required and how to set it.
- **No silent hang.** 1.0 read the engine's whole output before its 600 s timeout could start, so the timeout never fired and a
  stuck call blocked the server. 1.1.0 has no C# per-call layer to hang: the relay copies bytes both ways, the Python server
  handles each call, and closing the host's stdin ends both processes.
- **Reports in one place.** 1.0 set `SPINDOCTOR_WORKSPACE` to a `workspace` folder inside `${PLUGIN_DATA}` (client-managed).
  Now `~/spindoctor-workspace` (or a `workspace` argument). `PYTHONDONTWRITEBYTECODE` keeps the plugin folder unchanged.
- The repo root is the plugin (1.0 used a `spindoctor-qwerty-companion/` subfolder). plugin.json: author email, homepage,
  repository, license GPL-3.0-or-later, keywords for the simulator (1.0 had `presets`, `qwerty`).
- SKILL.md: server name, absolute paths, shell fallback, bundled-file examples that run as written, a no-Midjourney note.
- Tests: `tests/companion_standin_host.py`, a stand-in Agent Plugins host that runs the plugin as shipped and with the companion
  built from source (under Mono off Windows).
- License changed from MIT to GPL-3.0-or-later. Author RUSSELL PHILIP SMITHSON. README, NOTICE, COPYRIGHT and SPDX headers added.

## 1.0.0

- First release: `spindoctor-qwerty-companion/` with a prebuilt .NET Framework exe as the MCP server, engine described as
  SpinDoctor 3.0.3.
