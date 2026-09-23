"""Phase 1 スパイクの参考計測：起動にかかる時間と、常駐中のメモリ。使い捨て。

    python spikes/tools/footprint.py <pyside6|tauri|wpf>

3回起動し、起動の指示からログの start 行までの時間と、10秒放置後のメモリ（子プロセス込み）を測る。
Tauri は WebView2 の子プロセス群を持つので、子孫をすべて足す。
"""
import json
import os
import shutil
import subprocess
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
name = sys.argv[1]
from check import CANDIDATES, Log  # noqa: E402

PS = r"""
$root = %d
$all = Get-CimInstance Win32_Process | Select-Object ProcessId, ParentProcessId, Name
$ids = @($root); $grew = $true
while ($grew) { $grew = $false; foreach ($p in $all) { if ($ids -contains $p.ParentProcessId -and -not ($ids -contains $p.ProcessId)) { $ids += $p.ProcessId; $grew = $true } } }
$ps = Get-Process -Id $ids -ErrorAction SilentlyContinue
@{ n = $ps.Count; ws = ($ps | Measure-Object WorkingSet64 -Sum).Sum; priv = ($ps | Measure-Object PrivateMemorySize64 -Sum).Sum } | ConvertTo-Json -Compress
"""

run = os.path.join(ROOT, name, "run-footprint")
rows = []
for k in range(3):
    shutil.rmtree(run, ignore_errors=True)
    os.makedirs(run)
    log = Log(os.path.join(run, "spike.log"))
    t0 = time.perf_counter()
    subprocess.Popen(CANDIDATES[name]["cmd"] + ["--run-dir", run])
    i, line = log.wait("start ", timeout=60)
    ms = (time.perf_counter() - t0) * 1000
    pid = int(line.split("pid=")[1].split()[0])
    time.sleep(10)
    m = json.loads(subprocess.run(["pwsh", "-NoProfile", "-Command", PS % pid], capture_output=True, text=True).stdout)
    subprocess.run(["taskkill", "/F", "/T", "/PID", str(pid)], capture_output=True)
    rows.append((ms, m["n"], m["ws"] / 2**20, m["priv"] / 2**20))
    print(f"{name} #{k + 1} 起動 {ms:.0f}ms  プロセス {m['n']} 個  WS {m['ws'] / 2**20:.0f}MB  private {m['priv'] / 2**20:.0f}MB", flush=True)
    time.sleep(1)
