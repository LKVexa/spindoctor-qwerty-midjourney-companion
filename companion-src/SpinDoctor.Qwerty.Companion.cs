// SpinDoctor Qwerty 1.1.0 - SpinDoctor Qwerty Companion: native launcher for the bundled Python MCP server
// Copyright (C) 2026 RUSSELL PHILIP SMITHSON <russellsmithson77@outlook.com>
// SPDX-License-Identifier: GPL-3.0-or-later
// This program is free software: you can redistribute it and/or modify it under the terms of the GNU General
// Public License as published by the Free Software Foundation, either version 3 of the License, or (at your
// option) any later version. It is distributed WITHOUT ANY WARRANTY; see the LICENSE file for details.
//
// What it is: a small stdio launcher. An MCP host starts it as the plugin's server (Agent Plugins allows one executable token as
// the command, no arguments in it, so `py -3` cannot be written there). It finds a working Python 3 and relays the host's stdio,
// byte for byte, to the bundled engine's MCP server (skills/spindoctor-qwerty/scripts/spindoctor_mcp.py). All tools, schemas and
// results come from that server, so the companion cannot drift from the engine. It does not talk to Midjourney or any network.
//
// Python: $SPINDOCTOR_PYTHON (a command, arguments allowed, e.g. "py -3" or "C:\Python312\python.exe"), else the first of
// py -3, python, python3 (Windows) or python3, python (elsewhere) that reports major version 3. If none works, the companion answers
// every request with a JSON-RPC error that says so, then exits when the host closes stdin.
// Build (C# 5, .NET Framework 4.x, no packages): python3 tools/build_companion.py  - or by hand on Windows:
//   %WINDIR%\Microsoft.NET\Framework64\v4.0.30319\csc.exe /nologo /optimize+ /target:exe /out:server\SpinDoctor.Qwerty.Companion.exe companion-src\SpinDoctor.Qwerty.Companion.cs
using System;
using System.Collections.Generic;
using System.Diagnostics;
using System.IO;
using System.Reflection;
using System.Text;
using System.Text.RegularExpressions;
using System.Threading;

[assembly: AssemblyTitle("SpinDoctor Qwerty Companion")]
[assembly: AssemblyProduct("SpinDoctor Qwerty")]
[assembly: AssemblyCopyright("Copyright (C) 2026 RUSSELL PHILIP SMITHSON. GPL-3.0-or-later.")]
[assembly: AssemblyVersion("1.1.0.0")]
[assembly: AssemblyFileVersion("1.1.0.0")]

namespace SpinDoctor.Qwerty.Companion
{
    internal static class Program
    {
        internal const string Version = "1.1.0";
        private static bool IsWindows { get { return Path.DirectorySeparatorChar == '\\'; } }

        private static int Main(string[] args)
        {
            if (args.Length > 0 && (args[0] == "--version" || args[0] == "-v")) { Console.Out.WriteLine("SpinDoctor Qwerty Companion " + Version); return 0; }
            if (args.Length > 0 && args[0] == "--which-python")
            {
                string[] p = FindPython(); Console.Out.WriteLine(p == null ? "none" : string.Join(" ", p)); return p == null ? 1 : 0;
            }
            if (args.Length > 0) { Console.Error.WriteLine("usage: SpinDoctor.Qwerty.Companion.exe [--version | --which-python]  (no arguments: run as an MCP stdio server)"); return 2; }
            string server = Environment.GetEnvironmentVariable("SPINDOCTOR_QWERTY_MCP");
            if (string.IsNullOrEmpty(server))
                server = Path.GetFullPath(Path.Combine(ExeDir(), Path.Combine("..", Path.Combine("skills", Path.Combine("spindoctor-qwerty", Path.Combine("scripts", "spindoctor_mcp.py"))))));
            if (!File.Exists(server)) return Fallback("SpinDoctor engine not found at " + server + " (keep server\\ next to skills\\ in the plugin folder, or set SPINDOCTOR_QWERTY_MCP).");
            string[] py = FindPython();
            if (py == null) return Fallback("Python 3.8+ is required: set SPINDOCTOR_PYTHON (for example \"py -3\") or install Python from python.org. Tried: " + string.Join(", ", Candidates()));
            return Relay(py, server);
        }

        private static string ExeDir()
        {
            string loc = typeof(Program).Assembly.Location;
            return string.IsNullOrEmpty(loc) ? AppDomain.CurrentDomain.BaseDirectory : Path.GetDirectoryName(loc);
        }

        // ---------------------------------------------------------------- Python discovery
        internal static List<string[]> CandidateList()
        {
            var list = new List<string[]>();
            string env = Environment.GetEnvironmentVariable("SPINDOCTOR_PYTHON");
            if (!string.IsNullOrEmpty(env) && env.Trim().Length > 0) { list.Add(SplitCommand(env.Trim())); return list; }
            if (IsWindows) { list.Add(new[] { "py", "-3" }); list.Add(new[] { "python" }); list.Add(new[] { "python3" }); }
            else { list.Add(new[] { "python3" }); list.Add(new[] { "python" }); }
            return list;
        }

        private static IEnumerable<string> Candidates() { foreach (var c in CandidateList()) yield return string.Join(" ", c); }

        // "C:\Program Files\Python312\python.exe" -X utf8  ->  [C:\Program Files\Python312\python.exe, -X, utf8]
        internal static string[] SplitCommand(string s)
        {
            var parts = new List<string>();
            foreach (Match m in Regex.Matches(s, "\"([^\"]*)\"|(\\S+)")) parts.Add(m.Groups[1].Success ? m.Groups[1].Value : m.Groups[2].Value);
            return parts.ToArray();
        }

        private static string[] FindPython()
        {
            foreach (var c in CandidateList())
            {
                try
                {
                    var psi = Start(c, new[] { "-c", "import sys; print(sys.version_info[0])" });
                    psi.RedirectStandardInput = false;
                    using (var p = Process.Start(psi))
                    {
                        string o = p.StandardOutput.ReadToEnd();
                        p.StandardError.ReadToEnd();
                        if (!p.WaitForExit(20000)) { try { p.Kill(); } catch { } continue; }
                        // the Windows Store "python" alias exists on PATH but prints nothing useful: a probe, not a PATH lookup, decides
                        if (p.ExitCode == 0 && o.Trim() == "3") return c;
                    }
                }
                catch (Exception) { /* not installed: next candidate */ }
            }
            return null;
        }

        private static ProcessStartInfo Start(string[] cmd, string[] extra)
        {
            var args = new StringBuilder();
            for (int i = 1; i < cmd.Length; i++) args.Append(Quote(cmd[i])).Append(' ');
            foreach (var a in extra) args.Append(Quote(a)).Append(' ');
            var psi = new ProcessStartInfo(cmd[0], args.ToString().TrimEnd())
            {
                UseShellExecute = false, RedirectStandardInput = true, RedirectStandardOutput = true, RedirectStandardError = true, CreateNoWindow = true
            };
            psi.EnvironmentVariables["PYTHONUTF8"] = "1";
            psi.EnvironmentVariables["PYTHONIOENCODING"] = "utf-8";
            psi.EnvironmentVariables["PYTHONDONTWRITEBYTECODE"] = "1";
            return psi;
        }

        // Windows command-line quoting (CommandLineToArgvW rules); Mono applies the same rules on other systems.
        internal static string Quote(string a)
        {
            if (a.Length > 0 && a.IndexOfAny(new[] { ' ', '\t', '"' }) < 0) return a;
            var sb = new StringBuilder("\"");
            int bs = 0;
            foreach (char ch in a)
            {
                if (ch == '\\') { bs++; continue; }
                if (ch == '"') { sb.Append('\\', bs * 2 + 1).Append('"'); bs = 0; continue; }
                sb.Append('\\', bs).Append(ch); bs = 0;
            }
            sb.Append('\\', bs * 2).Append('"');
            return sb.ToString();
        }

        // ---------------------------------------------------------------- relay
        private static int Relay(string[] py, string server)
        {
            Process child;
            try { child = Process.Start(Start(py, new[] { server })); }
            catch (Exception e) { return Fallback("Could not start Python (" + string.Join(" ", py) + "): " + e.Message); }
            Stream hostIn = Console.OpenStandardInput(), hostOut = Console.OpenStandardOutput(), hostErr = Console.OpenStandardError();
            var toChild = new Thread(() =>
            {
                try { Pump(hostIn, child.StandardInput.BaseStream); } catch (Exception) { }
                try { child.StandardInput.Close(); } catch (Exception) { } // host closed stdin: the Python server sees EOF and exits
            }) { IsBackground = true };
            var fromChild = new Thread(() => { try { Pump(child.StandardOutput.BaseStream, hostOut); } catch (Exception) { } }) { IsBackground = true };
            var errChild = new Thread(() => { try { Pump(child.StandardError.BaseStream, hostErr); } catch (Exception) { } }) { IsBackground = true };
            toChild.Start(); fromChild.Start(); errChild.Start();
            child.WaitForExit();
            fromChild.Join(5000); errChild.Join(2000);
            return child.ExitCode;
        }

        private static void Pump(Stream from, Stream to)
        {
            var buf = new byte[65536];
            int n;
            while ((n = from.Read(buf, 0, buf.Length)) > 0) { to.Write(buf, 0, n); to.Flush(); }
        }

        // ---------------------------------------------------------------- no engine / no Python: say so over JSON-RPC
        private static int Fallback(string message)
        {
            Console.Error.WriteLine("spindoctor-qwerty-companion: " + message);
            var stdin = new StreamReader(Console.OpenStandardInput(), new UTF8Encoding(false));
            var stdout = new StreamWriter(Console.OpenStandardOutput(), new UTF8Encoding(false)) { AutoFlush = true, NewLine = "\n" };
            var idRx = new Regex("\"id\"\\s*:\\s*(\"(?:[^\"\\\\]|\\\\.)*\"|-?\\d+)");
            string line;
            while ((line = stdin.ReadLine()) != null)
            {
                Match m = idRx.Match(line);
                if (!m.Success) continue; // notifications get no reply
                stdout.WriteLine("{\"jsonrpc\":\"2.0\",\"id\":" + m.Groups[1].Value + ",\"error\":{\"code\":-32603,\"message\":\"" + JsonEscape(message) + "\"}}");
            }
            return 1;
        }

        internal static string JsonEscape(string s)
        {
            var sb = new StringBuilder();
            foreach (char c in s)
            {
                if (c == '"' || c == '\\') sb.Append('\\').Append(c);
                else if (c < ' ') sb.AppendFormat("\\u{0:x4}", (int)c);
                else sb.Append(c);
            }
            return sb.ToString();
        }
    }
}
