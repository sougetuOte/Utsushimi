// Phase 1 スパイク：.NET WPF。使い捨て。本体に持ち込まない。共通の約束は spikes/README.md。
using System;
using System.Diagnostics;
using System.IO;
using System.Runtime.InteropServices;
using System.Threading.Tasks;
using System.Windows;
using System.Windows.Controls;
using System.Windows.Input;
using System.Windows.Media;
using System.Windows.Threading;
using Microsoft.Data.Sqlite;
using Forms = System.Windows.Forms;

static class Program
{
    const string Title = "utsushimi-spike-wpf";
    const double Edge = 8;
    const double Bar = 22;

    static string runDir = Path.Combine(AppContext.BaseDirectory, "run");
    static string autoSend;
    static double bgSeconds = 3;
    static bool topmost;
    static StreamWriter log;
    static SqliteConnection db;
    static int shutdowns;

    [DllImport("kernel32.dll")] static extern IntPtr GetConsoleWindow();

    static void Log(string msg) => log.WriteLine($"{DateTime.Now:yyyy-MM-ddTHH:mm:ss.fff} {msg}");

    static long Persist(string role, string text)
    {
        using var cmd = db.CreateCommand();
        cmd.CommandText = "INSERT INTO messages(role, text, ts) VALUES($r, $t, $ts); SELECT last_insert_rowid();";
        cmd.Parameters.AddWithValue("$r", role);
        cmd.Parameters.AddWithValue("$t", text);
        cmd.Parameters.AddWithValue("$ts", DateTime.Now.ToString("o"));
        return (long)cmd.ExecuteScalar();
    }

    static void Exec(string sql)
    {
        using var cmd = db.CreateCommand();
        cmd.CommandText = sql;
        cmd.ExecuteNonQuery();
    }

    [STAThread]
    static void Main(string[] args)
    {
        for (int i = 0; i < args.Length; i++)
        {
            switch (args[i])
            {
                case "--run-dir": runDir = args[++i]; break;
                case "--auto-send": autoSend = args[++i]; break;
                case "--bg-seconds": bgSeconds = double.Parse(args[++i]); break;
                case "--topmost": topmost = true; break;
            }
        }
        Directory.CreateDirectory(runDir);
        log = new StreamWriter(Path.Combine(runDir, "spike.log"), true) { AutoFlush = true };
        db = new SqliteConnection($"Data Source={Path.Combine(runDir, "spike.db")}");
        db.Open();
        Exec("PRAGMA journal_mode=WAL");
        Exec("PRAGMA synchronous=FULL");
        Exec("CREATE TABLE IF NOT EXISTS messages(id INTEGER PRIMARY KEY, role TEXT, text TEXT, ts TEXT)");

        var app = new Application { ShutdownMode = ShutdownMode.OnExplicitShutdown };
        app.Exit += (_, _) => { shutdowns++; Log($"shutdown count={shutdowns}"); };

        var win = new Window
        {
            Title = Title, Width = 380, Height = 260, WindowStyle = WindowStyle.None, ResizeMode = ResizeMode.NoResize,
            Topmost = topmost, Background = new SolidColorBrush(Color.FromRgb(0x2b, 0x2b, 0x33)),
        };
        var grid = new Grid { Margin = new Thickness(12, 8, 12, 12) };
        grid.RowDefinitions.Add(new RowDefinition { Height = new GridLength(Bar) });
        grid.RowDefinitions.Add(new RowDefinition { Height = new GridLength(1, GridUnitType.Star) });
        grid.RowDefinitions.Add(new RowDefinition { Height = new GridLength(24) });
        var bar = new DockPanel();
        var close = new Button { Content = "×", Width = 22, Height = 22 };
        DockPanel.SetDock(close, Dock.Right);
        bar.Children.Add(close);
        bar.Children.Add(new TextBlock { Text = "相棒（spike）", Foreground = Brushes.Gainsboro, VerticalAlignment = VerticalAlignment.Center });
        Grid.SetRow(bar, 0);
        var transcript = new TextBox { IsReadOnly = true, Focusable = false, Margin = new Thickness(0, 4, 0, 4), TextWrapping = TextWrapping.Wrap };
        Grid.SetRow(transcript, 1);
        var row = new DockPanel();
        var send = new Button { Content = "送信", Width = 48, Margin = new Thickness(4, 0, 0, 0) };
        DockPanel.SetDock(send, Dock.Right);
        var input = new TextBox();
        row.Children.Add(send);
        row.Children.Add(input);
        Grid.SetRow(row, 2);
        grid.Children.Add(bar);
        grid.Children.Add(transcript);
        grid.Children.Add(row);
        win.Content = grid;

        using (var cmd = db.CreateCommand())
        {
            cmd.CommandText = "SELECT role, text FROM messages ORDER BY id";
            using var r = cmd.ExecuteReader();
            int loaded = 0;
            while (r.Read()) { transcript.AppendText($"{r.GetString(0)}: {r.GetString(1)}\n"); loaded++; }
            win.Tag = loaded;
        }

        void HideToTray() { win.Hide(); Log("hide"); }
        void ShowFromTray() { win.Show(); win.Activate(); Log("show"); }
        close.Click += (_, _) => HideToTray();
        win.Closing += (_, e) => { e.Cancel = true; HideToTray(); }; // Alt+F4 もトレイへ

        var moveTimer = new DispatcherTimer { Interval = TimeSpan.FromMilliseconds(300) };
        moveTimer.Tick += (_, _) => { moveTimer.Stop(); Log($"rect {win.Left} {win.Top} {win.ActualWidth} {win.ActualHeight}"); };
        win.LocationChanged += (_, _) => { moveTimer.Stop(); moveTimer.Start(); };

        win.PreviewMouseLeftButtonDown += (_, e) =>
        {
            var p = e.GetPosition(win);
            double w = win.ActualWidth, h = win.ActualHeight;
            if (p.X < Edge || p.Y < Edge || p.X >= w - Edge || p.Y >= h - Edge)
            {
                Log($"poke edge {(int)p.X} {(int)p.Y}");
                e.Handled = true;
                return;
            }
            Log($"click inner {(int)p.X} {(int)p.Y}");
            if (p.Y < Edge + Bar && !(e.OriginalSource is DependencyObject d && FindButton(d)))
            {
                e.Handled = true;
                win.DragMove();
            }
        };

        bool busy = false;
        double maxGap = 0;
        var sw = new Stopwatch();
        var ticker = new DispatcherTimer { Interval = TimeSpan.FromMilliseconds(20) };
        ticker.Tick += (_, _) => { maxGap = Math.Max(maxGap, sw.Elapsed.TotalMilliseconds); sw.Restart(); };

        async void Send()
        {
            var text = input.Text.Trim();
            if (text.Length == 0 || busy) return;
            input.Clear();
            var id = Persist("user", text);
            Log($"send id={id}");
            transcript.AppendText($"user: {text}\n");
            busy = true;
            maxGap = 0;
            sw.Restart();
            ticker.Start();
            Log("bg start");
            await Task.Run(() => Task.Delay(TimeSpan.FromSeconds(bgSeconds))); // LLM 呼び出しの代わりの待ち
            ticker.Stop();
            var rid = Persist("assistant", "（返事）");
            transcript.AppendText("assistant: （返事）\n");
            busy = false;
            Log($"bg end maxgap={maxGap:F0}ms input_during_bg=\"{input.Text}\"");
            Log($"reply id={rid}");
        }
        send.Click += (_, _) => Send();
        input.KeyDown += (_, e) => { if (e.Key == Key.Enter) Send(); };

        var menu = new Forms.ContextMenuStrip();
        menu.Items.Add("表示", null, (_, _) => ShowFromTray());
        menu.Items.Add("終了", null, (_, _) => app.Shutdown());
        var tray = new Forms.NotifyIcon { Icon = System.Drawing.SystemIcons.Application, Text = Title, ContextMenuStrip = menu, Visible = true };
        tray.MouseClick += (_, e) => { if (e.Button == Forms.MouseButtons.Left) ShowFromTray(); };
        app.Exit += (_, _) => tray.Dispose();

        win.Loaded += (_, _) =>
        {
            var console = GetConsoleWindow() == IntPtr.Zero ? "none" : "present";
            Log($"start pid={Environment.ProcessId} console={console} loaded={win.Tag} tray=true");
            Log($"rect {win.Left} {win.Top} {win.ActualWidth} {win.ActualHeight}");
            input.Focus();
            if (autoSend != null)
            {
                input.Text = autoSend;
                var t = new DispatcherTimer { Interval = TimeSpan.FromMilliseconds(200) };
                t.Tick += (_, _) => { t.Stop(); Send(); };
                t.Start();
            }
        };
        win.Show();
        app.Run();
    }

    static bool FindButton(DependencyObject d)
    {
        for (; d != null; d = d is Visual || d is System.Windows.Media.Media3D.Visual3D ? VisualTreeHelper.GetParent(d) : LogicalTreeHelper.GetParent(d))
            if (d is Button) return true;
        return false;
    }
}
