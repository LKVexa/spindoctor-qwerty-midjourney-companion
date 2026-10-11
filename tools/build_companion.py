#!/usr/bin/env python3
# SpinDoctor Qwerty 1.1.0 - build the SpinDoctor Qwerty Companion launcher from source (reproducible, no downloads)
# Copyright (C) 2026 RUSSELL PHILIP SMITHSON <russellsmithson77@outlook.com>
# SPDX-License-Identifier: GPL-3.0-or-later
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU General
# Public License as published by the Free Software Foundation, either version 3 of the License, or (at your
# option) any later version. It is distributed WITHOUT ANY WARRANTY; see the LICENSE file for details.
"""Build server/SpinDoctor.Qwerty.Companion.exe from companion-src/SpinDoctor.Qwerty.Companion.cs (C# 5, .NET Framework 4.x,
no NuGet packages, no network). Run from anywhere:

  py tools\\build_companion.py            (Windows)     python3 tools/build_companion.py    (macOS/Linux with Mono)
  ... --use      also point mcp.json at the companion (command ./server/SpinDoctor.Qwerty.Companion.exe)
  ... --unuse    point mcp.json back at python3 (the shipped default); does not build
  ... --out FILE build somewhere else (mcp.json untouched)

Compiler, first found: $CSC; on Windows the C# compiler that ships with .NET Framework 4.x
(%WINDIR%\\Microsoft.NET\\Framework64\\v4.0.30319\\csc.exe, then Framework\\); then `csc` on PATH (Roslyn: adds /deterministic);
then Mono's `mcs`. Writes server/BUILD_INFO.txt (compiler, SHA-256). Same source + same compiler -> same program; byte-identical
output only with Roslyn's /deterministic (the Framework csc and mcs stamp a fresh module id each build)."""
import argparse, datetime, hashlib, json, os, shutil, subprocess, sys
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, "companion-src", "SpinDoctor.Qwerty.Companion.cs")
EXE = os.path.join(ROOT, "server", "SpinDoctor.Qwerty.Companion.exe")
MCP = os.path.join(ROOT, "mcp.json")
SERVER = "spindoctor-qwerty-companion"


def find_compiler():
    if os.environ.get("CSC"): c = os.environ["CSC"]; return c, ("mcs" if os.path.basename(c).lower().startswith("mcs") else "csc")
    if os.name == "nt":
        win = os.environ.get("WINDIR", r"C:\Windows")
        for fw in ("Framework64", "Framework"):
            c = os.path.join(win, "Microsoft.NET", fw, "v4.0.30319", "csc.exe")
            if os.path.isfile(c): return c, "netfx"
    c = shutil.which("csc")
    if c: return c, "csc"
    c = shutil.which("mcs")
    if c: return c, "mcs"
    return None, None


def build(out):
    comp, kind = find_compiler()
    if not comp:
        sys.exit("No C# compiler found. Windows: .NET Framework 4.x ships csc.exe under %WINDIR%\\Microsoft.NET\\Framework64\\v4.0.30319\\ "
                 "(enable '.NET Framework 3.5/4.8' in Windows Features if missing). macOS/Linux: install Mono (mono-devel / mono-mcs). Or set CSC.")
    os.makedirs(os.path.dirname(os.path.abspath(out)), exist_ok=True)
    if kind == "mcs": argv = [comp, "-nologo", "-langversion:5", "-sdk:4.5", "-optimize+", "-target:exe", "-out:" + out, SRC]
    elif kind == "csc": argv = [comp, "/nologo", "/langversion:5", "/deterministic", "/optimize+", "/target:exe", "/out:" + out, SRC]
    else: argv = [comp, "/nologo", "/optimize+", "/target:exe", "/out:" + out, SRC]  # Framework csc: C# 5 by default
    r = subprocess.run(argv, capture_output=True, text=True)
    sys.stdout.write(r.stdout); sys.stderr.write(r.stderr)
    if r.returncode or not os.path.isfile(out): sys.exit("build failed (%s)" % " ".join(argv))
    sha = hashlib.sha256(open(out, "rb").read()).hexdigest()
    ver = (r.stdout + r.stderr).strip().splitlines()[:1]
    try: ver = subprocess.run([comp, "--version"] if kind == "mcs" else [comp, "/help"], capture_output=True, text=True, timeout=60).stdout.strip().splitlines()[:1]
    except Exception: pass
    info = ("SpinDoctor Qwerty Companion 1.1.0\nsource: companion-src/SpinDoctor.Qwerty.Companion.cs sha256 %s\ncompiler: %s (%s) %s\n"
            "output: %s sha256 %s (%d bytes)\nbuilt: %s\n") % (hashlib.sha256(open(SRC, "rb").read()).hexdigest(), os.path.basename(comp), kind,
            (ver[0] if ver else ""), os.path.basename(out), sha, os.path.getsize(out), datetime.datetime.now().strftime("%Y-%m-%d %H:%M"))
    open(os.path.join(os.path.dirname(os.path.abspath(out)), "BUILD_INFO.txt"), "w", encoding="utf-8").write(info)
    print("built %s\n  sha256 %s\n  compiler %s (%s)" % (out, sha, comp, kind))


def wire(use):
    c = json.load(open(MCP, encoding="utf-8")); s = c["mcpServers"][SERVER]
    if use:
        if not os.path.isfile(EXE): sys.exit("build first: " + EXE + " is missing")
        s["command"] = "./server/SpinDoctor.Qwerty.Companion.exe"; s["args"] = []
    else:
        s["command"] = "python3"; s["args"] = ["${PLUGIN_ROOT}/skills/spindoctor-qwerty/scripts/spindoctor_mcp.py"]
    open(MCP, "w", encoding="utf-8", newline="\n").write(json.dumps(c, indent=2) + "\n")
    print("mcp.json now starts:", s["command"], *s["args"])


ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
ap.add_argument("--use", action="store_true"); ap.add_argument("--unuse", action="store_true"); ap.add_argument("--out")
a = ap.parse_args()
if a.unuse: wire(False); sys.exit(0)
build(a.out or EXE)
if a.use and not a.out: wire(True)
