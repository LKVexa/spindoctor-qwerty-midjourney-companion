# server/

`tools/build_companion.py` writes the companion launcher here: `SpinDoctor.Qwerty.Companion.exe` (plus `BUILD_INFO.txt` with the
compiler and SHA-256). The repository does not ship the .exe - build it from `companion-src/` (no downloads on Windows: the C#
compiler comes with .NET Framework 4.x). `python3 tools/build_companion.py --use` builds it and points `mcp.json` at it.
