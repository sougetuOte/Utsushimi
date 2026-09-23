"""Phase 1 スパイクの計測。使い捨て。

    python spikes/tools/check.py <pyside6|tauri|wpf>

候補を実起動し、合成したマウス・キー入力と UI オートメーション（tools/tray.ps1。pwsh が要る）で S1〜S7 を測る。
結果は spikes/<候補>/run-check/result.txt。共通の約束は spikes/README.md。
"""
import ctypes
import os
import shutil
import sqlite3
import subprocess
import sys
import time
from ctypes import wintypes

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
u32 = ctypes.windll.user32
u32.SetProcessDpiAwarenessContext(ctypes.c_void_p(-4))  # per-monitor v2：座標は物理ピクセル

CANDIDATES = {
    "pyside6": {
        "cmd": [os.path.join(ROOT, "pyside6", ".venv", "Scripts", "python.exe"), os.path.join(ROOT, "pyside6", "spike.py")],
        "gui": [os.path.join(ROOT, "pyside6", ".venv", "Scripts", "pythonw.exe"), os.path.join(ROOT, "pyside6", "spike.py")],
    },
    "tauri": {
        "cmd": [os.path.join(ROOT, "tauri", "src-tauri", "target", "release", "spike-tauri.exe")],
    },
    "wpf": {
        "cmd": [os.path.join(ROOT, "wpf", "bin", "Release", "net10.0-windows", "SpikeWpf.exe")],
    },
}


def find(title, timeout=15):
    end = time.time() + timeout
    while time.time() < end:
        h = u32.FindWindowW(None, title)
        if h:
            return h
        time.sleep(0.1)
    raise RuntimeError(f"window not found: {title}")


def rect(h):
    # 見えている範囲（DWMWA_EXTENDED_FRAME_BOUNDS）。GetWindowRect は影つきの枠なし窓で見えない縁を含む
    r = wintypes.RECT()
    ctypes.windll.dwmapi.DwmGetWindowAttribute(h, 9, ctypes.byref(r), ctypes.sizeof(r))
    return r.left, r.top, r.right, r.bottom


def scale(h):
    return u32.GetDpiForWindow(h) / 96


MOUSEEVENTF_MOVE, MOUSEEVENTF_LEFTDOWN, MOUSEEVENTF_LEFTUP = 1, 2, 4


def click(x, y):
    u32.SetCursorPos(int(x), int(y))
    time.sleep(0.05)
    u32.mouse_event(MOUSEEVENTF_LEFTDOWN, 0, 0, 0, 0)
    time.sleep(0.05)
    u32.mouse_event(MOUSEEVENTF_LEFTUP, 0, 0, 0, 0)
    time.sleep(0.2)


def drag(x, y, dx, dy):
    u32.SetCursorPos(int(x), int(y))
    time.sleep(0.05)
    u32.mouse_event(MOUSEEVENTF_LEFTDOWN, 0, 0, 0, 0)
    time.sleep(0.15)
    for i in range(1, 21):
        u32.SetCursorPos(int(x + dx * i / 20), int(y + dy * i / 20))
        u32.mouse_event(MOUSEEVENTF_MOVE, 0, 0, 0, 0)
        time.sleep(0.02)
    time.sleep(0.1)
    u32.mouse_event(MOUSEEVENTF_LEFTUP, 0, 0, 0, 0)
    time.sleep(0.5)


class KI(ctypes.Structure):
    _fields_ = [("wVk", wintypes.WORD), ("wScan", wintypes.WORD), ("dwFlags", wintypes.DWORD),
                ("time", wintypes.DWORD), ("dwExtraInfo", ctypes.c_size_t)]


class INPUT(ctypes.Structure):
    class _U(ctypes.Union):
        _fields_ = [("ki", KI), ("pad", ctypes.c_byte * 32)]
    _anonymous_ = ("u",)
    _fields_ = [("type", wintypes.DWORD), ("u", _U)]


def key(vk=0, scan=0, flags=0):
    i = INPUT(type=1)
    i.ki = KI(vk, scan, flags, 0, 0)
    u32.SendInput(1, ctypes.byref(i), ctypes.sizeof(INPUT))


def type_text(text, enter=False):
    for ch in text:
        key(scan=ord(ch), flags=4)        # KEYEVENTF_UNICODE
        key(scan=ord(ch), flags=4 | 2)    # | KEYUP
        time.sleep(0.03)
    if enter:
        key(vk=0x0D)
        key(vk=0x0D, flags=2)
    time.sleep(0.2)


# 共通の配置（spikes/README.md）：論理ピクセルでの位置を物理へ
def pt_edge(h):
    l, t, r, b = rect(h)
    return l + 2, (t + b) / 2


def pt_inner(h):
    l, t, r, b = rect(h)
    return (l + r) / 2, t + (b - t) * 0.5


def pt_bar(h):
    l, t, r, b = rect(h)
    return l + (r - l) * 0.4, t + 19 * scale(h)


def pt_close(h):
    l, t, r, b = rect(h)
    return r - 23 * scale(h), t + 19 * scale(h)


def pt_input(h):
    l, t, r, b = rect(h)
    return l + (r - l) * 0.35, b - 24 * scale(h)


class Log:
    def __init__(self, path):
        self.path = path

    def lines(self):
        if not os.path.exists(self.path):
            return []
        with open(self.path, encoding="utf-8") as f:
            return f.read().splitlines()

    def wait(self, needle, after=0, timeout=15):
        end = time.time() + timeout
        while time.time() < end:
            ls = self.lines()
            for i in range(after, len(ls)):
                if needle in ls[i]:
                    return i, ls[i]
            time.sleep(0.05)
        raise RuntimeError(f"log timeout: {needle}")


def main():
    name = sys.argv[1]
    c = CANDIDATES[name]
    title = f"utsushimi-spike-{name}"
    run = os.path.join(ROOT, name, "run-check")
    shutil.rmtree(run, ignore_errors=True)
    os.makedirs(run)
    log = Log(os.path.join(run, "spike.log"))
    res = {}

    def launch(*extra):
        # venv の python.exe は実体を子に起こすことがあるので、殺すのはログに出た pid
        after = len(log.lines())
        subprocess.Popen(c["cmd"] + ["--run-dir", run, "--topmost", *extra])
        i, line = log.wait("start ", after, timeout=60)
        return int(line.split("pid=")[1].split()[0]), line

    def kill(pid):
        subprocess.run(["taskkill", "/F", "/PID", str(pid)], capture_output=True)

    def alive(pid):
        out = subprocess.run(["tasklist", "/FI", f"PID eq {pid}", "/NH"], capture_output=True, text=True).stdout
        return str(pid) in out

    def note(k, ok, how):
        res[k] = f"{'可' if ok else '不可'}  {how}"
        print(k, res[k], flush=True)

    # S4：1発言を残した直後に強制終了
    pid, _ = launch("--auto-send", "一言目", "--bg-seconds", "5")
    i, line = log.wait("send id=")
    kill(pid)
    time.sleep(0.5)
    con = sqlite3.connect(os.path.join(run, "spike.db"))
    n = con.execute("SELECT count(*) FROM messages WHERE text='一言目'").fetchone()[0]
    con.close()
    note("S4", n == 1, f"'{line.split(' ', 1)[1]}' の直後に taskkill /F → DB に '一言目' が {n} 行")

    # S6：2回目の起動
    pid, line = launch("--bg-seconds", "4")
    loaded = int(line.split("loaded=")[1].split()[0])
    note("S6", loaded >= 1, f"2回目の起動で '{line.split(' ', 1)[1]}'")
    h = find(title)
    time.sleep(1.0)

    # S2：ヘリと内側
    after = len(log.lines())
    click(*pt_edge(h))
    click(*pt_inner(h))
    ls = log.lines()[after:]
    e = [x for x in ls if "poke edge" in x]
    inn = [x for x in ls if "click inner" in x]
    note("S2", len(e) == 1 and len(inn) == 1, f"左縁2px のクリック → {len(e)} 件 poke edge、中央のクリック → {len(inn)} 件 click inner")

    # S1：上の帯をドラッグ
    r0 = rect(h)
    drag(*pt_bar(h), 120, 80)
    r1 = rect(h)
    note("S1", (r1[0] - r0[0], r1[1] - r0[1]) == (120, 80), f"窓の位置 {r0[:2]} → {r1[:2]}（+120,+80 をドラッグ）")

    # S5：裏の待ちの最中に打つ（1回目）・動かす（2回目）。
    # ドラッグ中は Windows の移動ループが UI スレッドを占めるので、間隔の計測は打つ回だけで見る
    after = len(log.lines())
    click(*pt_input(h))
    type_text("二言目", enter=True)
    log.wait("bg start", after)
    t0 = time.time()
    click(*pt_input(h))
    type_text("abc")
    during = time.time() - t0
    i, line = log.wait("bg end", after, timeout=10)
    gap = int(line.split("maxgap=")[1].split("ms")[0])
    typed = 'input_during_bg="abc"' in line
    after = len(log.lines())
    click(*pt_input(h))
    key(vk=0x23)  # End
    type_text("", enter=True)
    log.wait("bg start", after)
    r0 = rect(h)
    drag(*pt_bar(h), -60, -40)
    r1 = rect(h)
    i, line = log.wait("bg end", after, timeout=10)
    gap2 = int(line.split("maxgap=")[1].split("ms")[0])
    moved = (r1[0] - r0[0], r1[1] - r0[1]) == (-60, -40)
    note("S5", typed and moved and gap < 100,
         f"待ち4秒の最中（{during:.1f}秒で操作）に 'abc' 入力={typed}・UI タイマー（20ms）の最大間隔 {gap}ms。"
         f"次の待ちの最中にドラッグ {r0[:2]}→{r1[:2]}（ドラッグを含む回の最大間隔 {gap2}ms）")

    # S3：× で隠れる → トレイから表示・終了
    after = len(log.lines())
    click(*pt_close(h))
    time.sleep(0.5)
    vis = bool(u32.IsWindowVisible(h))
    live = alive(pid)
    hidden = not vis and live and any("hide" in x for x in log.lines()[after:])
    how = f"× をクリック → IsWindowVisible={vis}・プロセス生存={live}"
    tray = os.path.join(ROOT, "tools", "tray.ps1")
    subprocess.run(["pwsh", "-NoProfile", "-File", tray, name, "show"], capture_output=True)
    log.wait(" show", after, timeout=10)
    time.sleep(0.5)
    vis2 = bool(u32.IsWindowVisible(h))
    subprocess.run(["pwsh", "-NoProfile", "-File", tray, name, "quit"], capture_output=True)
    log.wait("shutdown count=", after, timeout=10)
    time.sleep(3)
    sd = [x for x in log.lines()[after:] if "shutdown count=" in x]
    gone = not alive(pid)
    how += (f"。トレイのアイコンを左クリック → IsWindowVisible={vis2}。右クリック→「終了」→ "
            f"shutdown の行 {len(sd)} 件・3秒後のプロセス消滅={gone}（tools/tray.ps1）")
    note("S3", hidden and vis2 and len(sd) == 1 and gone, how)

    # S7：ショートカットをシェル経由で開く
    gui = c.get("gui", c["cmd"])
    lnk = os.path.join(run, "spike.lnk")
    ps = (f"$s=(New-Object -ComObject WScript.Shell).CreateShortcut('{lnk}');"
          f"$s.TargetPath='{gui[0]}';$s.Arguments='{' '.join(gui[1:] + ['--run-dir', chr(34) + run + chr(34)])}';$s.Save()")
    subprocess.run(["powershell", "-NoProfile", "-Command", ps], check=True)
    after = len(log.lines())
    subprocess.run(["explorer.exe", lnk])
    i, line = log.wait("start ", after)
    pid = int(line.split("pid=")[1].split()[0])
    note("S7", "console=none" in line, f".lnk を explorer.exe で開く → '{line.split(' ', 1)[1]}'")
    kill(pid)

    with open(os.path.join(run, "result.txt"), "w", encoding="utf-8") as f:
        for k in sorted(res):
            f.write(f"{k} {res[k]}\n")


if __name__ == "__main__":
    main()
