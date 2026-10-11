#!/usr/bin/env python3
# SpinDoctor Qwerty 1.1.0 - SpinDoctor Qwerty Companion: stand-in Agent Plugins host and host check
# Copyright (C) 2026 RUSSELL PHILIP SMITHSON <russellsmithson77@outlook.com>
# SPDX-License-Identifier: GPL-3.0-or-later
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU General
# Public License as published by the Free Software Foundation, either version 3 of the License, or (at your
# option) any later version. It is distributed WITHOUT ANY WARRANTY; see the LICENSE file for details.
"""Stand-in Agent Plugins 1.0.0 host. Run from the repo root:

  python3 tests/companion_standin_host.py                       # install this folder, start the server, call every tool
  python3 tests/companion_standin_host.py --source https://github.com/LKVexa/spindoctor-qwerty-midjourney-companion

There is no Midjourney host to test against: Midjourney has no plugin or MCP interface. This script plays a generic Agent Plugins
1.0.0 client instead (closed manifest schema and name rules, fixed component locations, Agent Skills frontmatter, the closed stdio
server variant, a bare or ./ command without placeholders, ${PLUGIN_ROOT}/${PLUGIN_DATA} expansion in args/env/cwd,
PLUGIN_ROOT/PLUGIN_DATA in the server environment, plugin root as default cwd, containment) and speaks MCP over stdio to the
plugin's server exactly as configured - first as shipped (python3), then with the companion launcher built from source
(tools/build_companion.py --use). Off Windows the launcher runs under Mono, as a client may use a platform launcher for an
executable (spec 7.2.1); on Windows it runs directly. If no C# compiler is found the companion checks fail and say so.
Not tested: any real host's UI or installer, a real model choosing the tools, Windows/.NET Framework itself, macOS. Stdlib only.
"""
import hashlib, json, os, re, shutil, subprocess, sys, tempfile
sys.dont_write_bytecode = True; os.environ["PYTHONDONTWRITEBYTECODE"] = "1"
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)
PSCHEMA = "https://agent-plugins.org/schemas/1.0.0/plugin.schema.json"; MSCHEMA = "https://agent-plugins.org/schemas/1.0.0/mcp.schema.json"
TOOLS = ["spindoctor_functions", "spindoctor_list_presets", "spindoctor_report", "spindoctor_run_preset", "spindoctor_run_script", "spindoctor_test_theory"]
SID = "spindoctor-qwerty-companion"; EXE = "SpinDoctor.Qwerty.Companion.exe"
R = []
OK = lambda s: bool(re.search(r'"ok":\s*true', s or ""))


def T(name, ok, detail=""):
    R.append({"check": name, "pass": bool(ok), "detail": str(detail)[:600]})
    print(("PASS " if ok else "FAIL ") + name + ("" if ok else "  -- " + str(detail)[:500])); sys.stdout.flush()


# ---------------------------------------------------------------- loader (Agent Plugins 1.0.0)
def inside(root, p):
    r = os.path.realpath(root); q = os.path.realpath(p)
    return q == r or q.startswith(r + os.sep)


def valid_name(n):
    return isinstance(n, str) and 1 <= len(n) <= 64 and re.fullmatch(r"[a-z0-9](?:[a-z0-9.-]*[a-z0-9])?", n) and "--" not in n and ".." not in n


def frontmatter(text):
    if not text.startswith("---\n"): return None
    end = text.find("\n---", 4)
    if end < 0: return None
    out, cur = {}, None
    for ln in text[4:end].splitlines():
        if not ln.strip(): continue
        if ln.startswith("  ") and cur == "metadata":
            k, _, v = ln.strip().partition(":"); out["metadata"][k.strip()] = v.strip().strip('"'); continue
        k, _, v = ln.partition(":"); k = k.strip(); v = v.strip(); cur = k
        out[k] = {} if (k == "metadata" and not v) else v.strip('"')
    return out


def load_plugin(root):
    """Return (plugin dict, errors). Fatal manifest errors -> power None (plugin rejected)."""
    errs = []; mp = os.path.join(root, "plugin.json")
    if not os.path.isfile(mp) or not inside(root, mp): return None, ["no plugin.json in the plugin root"]
    try: m = json.load(open(mp, encoding="utf-8"))
    except ValueError as e: return None, ["plugin.json is not JSON: %s" % e]
    if not isinstance(m, dict): return None, ["plugin.json is not an object"]
    allowed = {"$schema", "name", "version", "description", "author", "homepage", "repository", "license", "keywords", "extensions"}
    for k in set(m) - allowed: errs.append("unknown manifest field ignored: %s" % k)
    if m.get("$schema") != PSCHEMA: return None, ["unsupported $schema %r" % m.get("$schema")]
    if not valid_name(m.get("name")): return None, ["invalid name %r" % m.get("name")]
    for k in ("version", "description", "homepage", "repository", "license"):
        if k in m and not isinstance(m[k], str): return None, ["%s must be a string" % k]
    a = m.get("author")
    if a is not None and (not isinstance(a, dict) or set(a) - {"name", "email", "url"} or not all(isinstance(v, str) for v in a.values())):
        return None, ["author must be an object with only string name/email/url"]
    kw = m.get("keywords")
    if kw is not None and (not isinstance(kw, list) or not all(isinstance(x, str) for x in kw)): return None, ["keywords must be a string array"]
    p = {"root": root, "manifest": m, "name": m["name"], "skills": {}, "servers": {}, "errors": errs}
    sd = os.path.join(root, "skills")
    if os.path.isdir(sd) and inside(root, sd):
        for d in sorted(os.listdir(sd)):
            f = os.path.join(sd, d, "SKILL.md")
            if not os.path.isfile(f) or not inside(root, f): continue
            text = open(f, encoding="utf-8").read(); fm = frontmatter(text) or {}
            n = fm.get("name", ""); desc = fm.get("description", "")
            bad = []
            if n != d or not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", n or "-") or len(n) > 64: bad.append("name must equal the folder and be lowercase-hyphen <= 64")
            if not desc or len(desc) > 1024: bad.append("description 1..1024 chars")
            if len(fm.get("compatibility", "")) > 500: bad.append("compatibility > 500 chars")
            if "metadata" in fm and not isinstance(fm["metadata"], dict): bad.append("metadata must be a map")
            if bad: errs.append("skill %s skipped: %s" % (d, "; ".join(bad))); continue
            p["skills"][n] = {"dir": os.path.join(sd, d), "frontmatter": fm, "body": text}
    mj = os.path.join(root, "mcp.json")
    if os.path.isfile(mj) and inside(root, mj):
        try: c = json.load(open(mj, encoding="utf-8"))
        except ValueError: c = None
        if not isinstance(c, dict) or set(c) != {"$schema", "mcpServers"} or c["$schema"] != MSCHEMA or not isinstance(c["mcpServers"], dict):
            errs.append("mcp.json invalid: MCP disabled for this plugin")
        else:
            for sname, s in c["mcpServers"].items():
                why = server_problem(root, s)
                if why: errs.append("server %s skipped: %s" % (sname, why)); continue
                p["servers"]["%s/%s" % (m["name"], sname)] = s
    return p, errs


def server_problem(root, s):
    if not isinstance(s, dict) or s.get("type") != "stdio": return "only the stdio variant is used by this stand-in"
    if set(s) - {"type", "command", "args", "env", "cwd"}: return "unknown field(s) %s" % sorted(set(s) - {"type", "command", "args", "env", "cwd"})
    cmd = s.get("command")
    if not isinstance(cmd, str) or not cmd or " " in cmd or "${" in cmd: return "command must be one executable token without placeholders"
    if cmd.startswith("./"):
        if not inside(root, os.path.join(root, cmd)): return "command escapes the plugin root"
    elif "/" in cmd or "\\" in cmd: return "command must be a bare name or ./path"
    if "args" in s and (not isinstance(s["args"], list) or not all(isinstance(x, str) for x in s["args"])): return "args must be strings"
    env = s.get("env", {})
    if not isinstance(env, dict) or not all(isinstance(v, str) for v in env.values()): return "env must map strings"
    if {"PLUGIN_ROOT", "PLUGIN_DATA"} & {k.upper() for k in env}: return "env must not set PLUGIN_ROOT/PLUGIN_DATA"
    cwd = s.get("cwd")
    if cwd is not None and not (cwd.startswith("./") or cwd == "${PLUGIN_ROOT}" or cwd.startswith("${PLUGIN_ROOT}/") or cwd == "${PLUGIN_DATA}" or cwd.startswith("${PLUGIN_DATA}/")):
        return "cwd form not allowed"
    return None


class Host:
    """Throwaway client home: installs plugins (copy of a folder or a git clone) and runs their MCP servers."""
    def __init__(self):
        self.home = tempfile.mkdtemp(prefix="sdq_ap_"); self.inst = os.path.join(self.home, "plugins"); self.data = os.path.join(self.home, "plugin-data")
        os.makedirs(self.inst); os.makedirs(self.data); self.extra_env = {}
        self.env = dict(os.environ, HOME=self.home, USERPROFILE=self.home); self.env.pop("SPINDOCTOR_WORKSPACE", None); self.env.pop("SPINDOCTOR_PYTHON", None)

    def install(self, src):
        if re.match(r"https://github\.com/", src):
            tmp = os.path.join(self.home, "clone"); subprocess.run(["git", "clone", "-q", "--depth", "1", src, tmp], check=True); src = tmp
        p, errs = load_plugin(src)
        if p is None: return None, errs
        dst = os.path.join(self.inst, p["name"]); shutil.rmtree(dst, ignore_errors=True)
        shutil.copytree(src, dst, ignore=shutil.ignore_patterns(".git", "__pycache__", "*.pyc"))
        return load_plugin(dst)

    def start(self, p, sid):
        return Mcp(p, sid, p["servers"][sid], self)

    def close(self):
        shutil.rmtree(self.home, ignore_errors=True)


def expand(v, root, data):
    return v.replace("${PLUGIN_ROOT}", root).replace("${PLUGIN_DATA}", data)


class Mcp:
    def __init__(self, p, name, cfg, host):
        root = os.path.realpath(p["root"]); data = os.path.join(host.data, p["name"]); os.makedirs(data, exist_ok=True)
        cmd = cfg["command"]; cmd = os.path.join(root, cmd[2:]) if cmd.startswith("./") else (shutil.which(cmd) or cmd)
        env = dict(host.env); env.update({k: expand(v, root, data) for k, v in cfg.get("env", {}).items()})
        env["PLUGIN_ROOT"] = root; env["PLUGIN_DATA"] = data
        cwd = expand(cfg.get("cwd", "${PLUGIN_ROOT}"), root, data); cwd = os.path.join(root, cwd[2:]) if cwd.startswith("./") else cwd
        self.argv = [cmd] + [expand(a, root, data) for a in cfg.get("args", [])]; self.name = name; self.cwd = cwd
        if cmd.lower().endswith(".exe") and os.name != "nt": self.argv = [shutil.which("mono") or "mono"] + self.argv  # platform launcher for a .NET exe
        env.update(host.extra_env)
        self.proc = subprocess.Popen(self.argv, cwd=cwd, env=env, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True, encoding="utf-8")
        self.n = 0
        self.init = self.rpc("initialize", {"protocolVersion": "2025-06-18", "capabilities": {}, "clientInfo": {"name": "agent-plugins-standin", "version": "1.1.0"}})
        self.proc.stdin.write(json.dumps({"jsonrpc": "2.0", "method": "notifications/initialized"}) + "\n"); self.proc.stdin.flush()
        self.tools = {t["name"]: t for t in (self.rpc("tools/list", {}).get("result", {}).get("tools", []))}

    def rpc(self, method, params):
        self.n += 1; self.proc.stdin.write(json.dumps({"jsonrpc": "2.0", "id": self.n, "method": method, "params": params}) + "\n"); self.proc.stdin.flush()
        while True:
            line = self.proc.stdout.readline()
            if not line: return {"error": "server closed"}
            try: msg = json.loads(line)
            except ValueError: continue
            if msg.get("id") == self.n: return msg

    def call(self, tool, args):
        r = self.rpc("tools/call", {"name": tool, "arguments": args}).get("result", {})
        return "\n".join(c.get("text", "") for c in r.get("content", []) if c.get("type") == "text")

    def close(self):
        try: self.proc.stdin.close(); self.proc.wait(timeout=10)
        except Exception: self.proc.kill()


# ---------------------------------------------------------------- checks
def negative():
    """The loader must refuse what Agent Plugins 1.0.0 refuses (so a pass below means something)."""
    base = tempfile.mkdtemp(prefix="sdq_ap_neg_"); src = os.path.join(base, "p")
    shutil.copytree(ROOT, src, ignore=shutil.ignore_patterns(".git", "__pycache__", "tests", "examples", "spindoctor", "server"))
    m = json.load(open(os.path.join(src, "plugin.json"))); c = json.load(open(os.path.join(src, "mcp.json")))
    def with_(mm=None, cc=None):
        json.dump(mm or m, open(os.path.join(src, "plugin.json"), "w")); json.dump(cc or c, open(os.path.join(src, "mcp.json"), "w"))
        return load_plugin(src)
    bad = 0
    for mm in ({**m, "name": "SpinDoctor"}, {**m, "author": {"name": "x", "company": "y"}}, {**m, "keywords": "quantum"}, {**m, "$schema": "https://example.com/x.json"}):
        bad += with_(mm)[0] is None
    srv = c["mcpServers"][SID]
    for s in ({**srv, "command": "py -3"}, {**srv, "command": "../server/" + EXE}, {**srv, "command": "${PLUGIN_ROOT}/server/" + EXE}, {**srv, "env": {"PLUGIN_ROOT": "/x"}},
              {**srv, "cwd": "/tmp"}, {**srv, "timeout": 5}):
        p, _ = with_(m, {**c, "mcpServers": {SID: s}}); bad += bool(p) and not p["servers"]
    shutil.rmtree(base, ignore_errors=True)
    T("stand-in loader refuses 4 bad manifests (uppercase name, extra author field, keywords not a list, unknown $schema) and skips 6 bad servers "
      "('py -3' as command, ../ command, placeholder in command, env PLUGIN_ROOT, absolute cwd, unknown field)", bad == 10, bad)


def static():
    m = json.load(open(os.path.join(ROOT, "plugin.json"), encoding="utf-8"))
    T("plugin.json: version 1.1.0, GPL-3.0-or-later, author name/email, homepage/repository, honest description (not a Midjourney integration)",
      m.get("version") == "1.1.0" and m.get("license") == "GPL-3.0-or-later" and m["author"].get("name") == "RUSSELL PHILIP SMITHSON"
      and m.get("repository", "").endswith("/spindoctor-qwerty-midjourney-companion") and "Not a Midjourney integration" in m.get("description", ""), m.get("description"))
    c = json.load(open(os.path.join(ROOT, "mcp.json"), encoding="utf-8"))["mcpServers"][SID]
    T("mcp.json as shipped starts python3 with the bundled server (the .exe is not in the repo)", c["command"] == "python3"
      and c["args"] == ["${PLUGIN_ROOT}/skills/spindoctor-qwerty/scripts/spindoctor_mcp.py"] and not os.path.exists(os.path.join(ROOT, "server", EXE)) or
      subprocess.run(["git", "-C", ROOT, "ls-files", "server/" + EXE], capture_output=True, text=True).stdout.strip() == "", c)
    src = [os.path.join(d, f) for d, _, fs in os.walk(ROOT) if "/.git" not in d and "__pycache__" not in d for f in fs if f.endswith((".py", ".cs"))]
    bad = [x for x in src if "SPDX-License-Identifier: GPL-3.0-or-later" not in open(x, encoding="utf-8").read(2500)]
    T("every .py/.cs file has a GPL-3.0-or-later SPDX header (%d files)" % len(src), not bad, bad[:3])
    tracked = subprocess.run(["git", "-C", ROOT, "ls-files"], capture_output=True, text=True).stdout.split()
    T("no binaries tracked in git (no .exe/.dll/.pdb)", not [x for x in tracked if x.lower().endswith((".exe", ".dll", ".pdb"))], [x for x in tracked if x.endswith(".exe")])
    links = [os.path.join(d, f) for d, ds, fs in os.walk(ROOT) for f in fs + ds if os.path.islink(os.path.join(d, f))]
    T("no symlinks in the package (containment rule)", not links, links)
    sk = os.path.join(ROOT, "skills", "spindoctor-qwerty"); t = open(os.path.join(sk, "SKILL.md"), encoding="utf-8").read()
    T("SKILL.md: guardrail, server name, absolute-path rule, no-Midjourney note, no host variables", "not a\nquantum computer" in t
      and "`spindoctor-qwerty-companion`" in t and "ABSOLUTE paths" in t and "Nothing here talks to Midjourney" in t and not re.search(r"\$\{[A-Z_]+\}", t))
    cmds = [ln.split("  #")[0].strip() for blk in re.findall(r"```bash\n(.*?)```", t, re.S) for ln in blk.splitlines() if ln.startswith("python3 scripts/")]
    ws = tempfile.mkdtemp(prefix="sdq_cli_"); bad = []
    for cm in cmds:
        argv = cm.split(" ", 2); rest = re.findall(r'"[^"]*"|\S+', argv[2])
        r = subprocess.run([sys.executable, argv[1], "--workspace", ws] + [x.strip('"') for x in rest], cwd=sk, capture_output=True, timeout=300)
        if r.returncode: bad.append((cm, r.stderr[-200:]))
    T("shell fallback: every CLI command in SKILL.md runs as written from the skill folder (%d commands)" % len(cmds), cmds and not bad, bad)
    shutil.rmtree(ws, ignore_errors=True)
    negative()


def exercise(h, p, sid, label):
    """Start the configured server and call all 6 tools; returns tools/list for the parity check."""
    srv = h.start(p, sid); root = os.path.realpath(p["root"])
    try:
        T(label + ": server started as configured, MCP initialize ok, cwd = plugin root", "serverInfo" in json.dumps(srv.init) and srv.cwd == root, (srv.argv, srv.init))
        T(label + ": tools/list returns the 6 SpinDoctor tools (spindoctor_functions marked read-only)", sorted(srv.tools) == TOOLS
          and (srv.tools.get("spindoctor_functions", {}).get("annotations") or {}).get("readOnlyHint") is True, sorted(srv.tools))
        r = srv.call("spindoctor_functions", {}); T(label + ": spindoctor_functions -> the Markdown function table", "| Function | What it does | Command to type |" in r, r[:150])
        r = srv.call("spindoctor_run_script", {"script": "q.circuit new bell 2\nq.circuit add h 0\nq.circuit add cx 0 1\nq.circuit run shots 1000 basis z"})
        T(label + ": Bell circuit ok, reports under ~/spindoctor-workspace", OK(r) and os.path.join(h.home, "spindoctor-workspace") in r, r[:200])
        r = srv.call("spindoctor_run_preset", {"preset_id": "qc-001"}); T(label + ": run_preset qc-001", OK(r) and "qc-001" in r, r[:200])
        r = srv.call("spindoctor_list_presets", {"filter": "ghz"}); T(label + ": list_presets ghz", OK(r) and "ghz" in r.lower(), r[:200])
        r = srv.call("spindoctor_report", {}); T(label + ": report lists the newest reports", OK(r) and ".txt" in r, r[:200])
        r = srv.call("spindoctor_run_script", {"script": "q.circuit new big 298\nq.circuit add h 0\nq.circuit add mcx7 0 1 2 3 4 5 6 297\nq.circuit run shots 64 basis z"})
        T(label + ": 298-qubit wide register with mcx7 (3.1.2 parity)", OK(r), r[:200])
        th = os.path.join(root, "skills", "spindoctor-qwerty", "examples", "theory", "hadamard_theory.txt")
        r = srv.call("spindoctor_test_theory", {"action": "extract", "source": "file", "path": th}); T(label + ": theory extract from an absolute path", OK(r), r[:200])
        r = srv.call("spindoctor_test_theory", {"action": "run", "source": "chat", "text": "From our chat: H then CX makes a Bell state.",
              "excerpts": ["User: does H then CNOT give 50/50 on 00 and 11?", "Assistant: yes, that is a Bell state."],
              "hypothesis": "H(0) then CX(0,1) gives P(00) = P(11) = 0.5", "prediction": "P(11) = 0.5 +/- 0.05 over 4000 shots",
              "script": "q.circuit new bt 2\nq.circuit add h 0\nq.circuit add cx 0 1\nq.circuit run shots 4000 basis z",
              "checks": [{"kind": "probability", "outcome": "11", "expected": 0.5, "tolerance": 0.05}]})
        pdf = re.findall(r'"([^"]+theory[^"]*\.pdf)"', r)
        T(label + ": theory from the chat: supported, 2 excerpts, valid PDF", '"verdict": "supported"' in r and '"excerptsRecorded": 2' in r
          and pdf and open(pdf[0], "rb").read(5) == b"%PDF-", r[:300])
        return srv.rpc("tools/list", {}).get("result")
    finally:
        srv.close()


def standin(source):
    h = Host()
    try:
        p, errs = h.install(source or ROOT)
        T("install from %s: manifest valid, no loader warnings" % ("GitHub (" + source + ")" if source else "a folder"), p is not None and not errs, errs)
        if not p: return
        T("discovered 1 skill (spindoctor-qwerty) and 1 stdio server (spindoctor-qwerty-companion/spindoctor-qwerty-companion)",
          list(p["skills"]) == ["spindoctor-qwerty"] and list(p["servers"]) == ["%s/%s" % (p["name"], SID)], (list(p["skills"]), list(p["servers"])))
        sid = list(p["servers"])[0]; root = p["root"]
        before = sorted(os.path.relpath(os.path.join(d, f), root) for d, _, fs in os.walk(root) for f in fs)
        tl_py = exercise(h, p, sid, "python3 server (as shipped)")
        after = sorted(os.path.relpath(os.path.join(d, f), root) for d, _, fs in os.walk(root) for f in fs)
        T("installed plugin folder unchanged by tool use (no __pycache__, reports outside)", before == after, set(after) ^ set(before))
        # ---- the companion: build from source inside the installed copy, wire it, run the same calls through it
        b = subprocess.run([sys.executable, os.path.join(root, "tools", "build_companion.py"), "--use"], capture_output=True, text=True, timeout=600)
        exe = os.path.join(root, "server", EXE)
        T("tools/build_companion.py --use builds server/%s from companion-src/ and points mcp.json at ./server/%s" % (EXE, EXE),
          b.returncode == 0 and os.path.isfile(exe) and json.load(open(os.path.join(root, "mcp.json")))["mcpServers"][SID]["command"] == "./server/" + EXE, (b.stdout + b.stderr)[-400:])
        if not os.path.isfile(exe): return
        info = open(os.path.join(root, "server", "BUILD_INFO.txt")).read()
        T("server/BUILD_INFO.txt records compiler and the exe's SHA-256", hashlib.sha256(open(exe, "rb").read()).hexdigest() in info, info)
        p2, errs2 = load_plugin(root)
        T("rewired mcp.json is still valid Agent Plugins (plugin-relative ./ command, no args)", p2 and not errs2 and list(p2["servers"]) == [sid], errs2)
        tl_exe = exercise(h, p2, sid, "companion launcher")
        T("companion's tools/list is identical to the Python server's (it relays, it cannot drift)", tl_exe == tl_py and tl_py is not None)
        launch = [shutil.which("mono") or "mono", exe] if os.name != "nt" else [exe]
        v = subprocess.run(launch + ["--version"], capture_output=True, text=True, timeout=60).stdout.strip()
        w = subprocess.run(launch + ["--which-python"], capture_output=True, text=True, timeout=60, env=h.env).stdout.strip()
        T("companion --version / --which-python: 'SpinDoctor Qwerty Companion 1.1.0', a Python 3 found by probing", v == "SpinDoctor Qwerty Companion 1.1.0" and w in ("python3", "python", "py -3"), (v, w))
        e = dict(h.env, SPINDOCTOR_PYTHON='"%s" -X utf8' % sys.executable)
        w = subprocess.run(launch + ["--which-python"], capture_output=True, text=True, timeout=60, env=e).stdout.strip()
        T("SPINDOCTOR_PYTHON with a quoted path plus arguments is honoured (1.0 treated the whole value as a file name)", w == "%s -X utf8" % sys.executable, w)
        h.extra_env = {"SPINDOCTOR_PYTHON": os.path.join(h.home, "no-such-python")}
        srv = h.start(p2, sid); r = srv.rpc("tools/list", {}); srv.close(); h.extra_env = {}
        T("no Python: every request gets a JSON-RPC error that says Python 3.8+ is required (no hang, no crash)",
          "Python 3.8+ is required" in json.dumps(srv.init) and "Python 3.8+ is required" in json.dumps(r), (srv.init, r))
        u = subprocess.run([sys.executable, os.path.join(root, "tools", "build_companion.py"), "--unuse"], capture_output=True, text=True)
        orig = open(os.path.join(ROOT if not source else os.path.join(h.home, "clone"), "mcp.json"), "rb").read()
        T("build_companion.py --unuse restores the shipped mcp.json byte for byte", open(os.path.join(root, "mcp.json"), "rb").read() == orig, u.stdout)
        o2 = os.path.join(h.home, "rebuild", EXE)
        subprocess.run([sys.executable, os.path.join(root, "tools", "build_companion.py"), "--out", o2], capture_output=True, text=True, timeout=600)
        T("rebuild from the same source gives the same program (same size; byte-identical only with Roslyn /deterministic)",
          os.path.isfile(o2) and os.path.getsize(o2) == os.path.getsize(exe), (os.path.getsize(exe), os.path.exists(o2) and os.path.getsize(o2)))
        # shared end-to-end suite through the companion launcher
        h.extra_env = {}
        subprocess.run([sys.executable, os.path.join(root, "tools", "build_companion.py"), "--use"], capture_output=True, timeout=600)
        out = os.path.join(HERE, "e2e_results.json")
        rr = subprocess.run([sys.executable, os.path.join(HERE, "e2e_mcp.py"), "--server"] + launch + ["--examples", os.path.join(root, "skills", "spindoctor-qwerty", "examples", "theory"),
                            "--out", out], env=h.env, cwd=root, capture_output=True, text=True, timeout=3600)
        last = [l for l in rr.stdout.splitlines() if l.strip()][-1:] or [""]
        T("shared end-to-end suite through the companion launcher: " + last[0][:60], rr.returncode == 0, rr.stdout[-400:])
    finally:
        h.close()


def main():
    a = sys.argv[1:]; opt = dict(zip(a[::2], a[1::2]))
    static(); standin(opt.get("--source"))
    mono = ""
    try: mono = subprocess.run(["mono", "--version"], capture_output=True, text=True).stdout.splitlines()[0]
    except Exception: pass
    json.dump({"python": sys.version.split()[0], "host": "stand-in Agent Plugins 1.0.0 client", "runtime": mono or ("Windows .NET Framework" if os.name == "nt" else ""), "checks": R},
              open(opt.get("--out", os.path.join(HERE, "host_check.json")), "w"), indent=1)
    n = sum(r["pass"] for r in R); print("%d/%d passed" % (n, len(R))); return 0 if n == len(R) else 1


if __name__ == "__main__":
    sys.exit(main())
