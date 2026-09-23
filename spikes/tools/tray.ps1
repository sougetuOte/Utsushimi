# PowerShell 7（pwsh）で走らせる。Windows PowerShell 5 は BOM 無しの UTF-8 を読めない。
# Phase 1 スパイクの計測：トレイのアイコンを UI オートメーションで押す。使い捨て。
#   pwsh -NoProfile -File spikes/tools/tray.ps1 <name> <show|quit>
# show：アイコンを左クリック相当（Invoke）。quit：右クリックでメニューを開き「終了」を Invoke。
param([string]$Name, [string]$Action)
Add-Type -AssemblyName UIAutomationClient, UIAutomationTypes, System.Windows.Forms
$root = [System.Windows.Automation.AutomationElement]::RootElement
$cond = New-Object System.Windows.Automation.PropertyCondition([System.Windows.Automation.AutomationElement]::NameProperty, "utsushimi-spike-$Name")
function Find-Icon {
    $root.FindAll([System.Windows.Automation.TreeScope]::Descendants, $cond) |
        Where-Object { $_.Current.ControlType -eq [System.Windows.Automation.ControlType]::Button } |
        Select-Object -First 1
}
$tray = Find-Icon
if (-not $tray) {
    # Windows 11 は新しいアイコンを「隠れているインジケーター」にしまう。開いてから探す
    $oc = New-Object System.Windows.Automation.PropertyCondition([System.Windows.Automation.AutomationElement]::ClassNameProperty, 'SystemTray.NormalButton')
    $over = $root.FindFirst([System.Windows.Automation.TreeScope]::Descendants, $oc)
    $over.GetCurrentPattern([System.Windows.Automation.InvokePattern]::Pattern).Invoke()
    Start-Sleep -Milliseconds 800
    $tray = Find-Icon
    Write-Output "opened overflow"
}
if (-not $tray) { Write-Output "icon not found"; exit 2 }
$r = $tray.Current.BoundingRectangle
Write-Output "icon at $($r.X),$($r.Y) $($r.Width)x$($r.Height)"
Add-Type @'
using System; using System.Runtime.InteropServices;
public static class M {
  [DllImport("user32.dll")] public static extern bool SetCursorPos(int x, int y);
  [DllImport("user32.dll")] public static extern void mouse_event(int f, int x, int y, int d, int e);
}
'@
$x = [int]($r.X + $r.Width / 2); $y = [int]($r.Y + $r.Height / 2)
[M]::SetCursorPos($x, $y) | Out-Null
Start-Sleep -Milliseconds 100
if ($Action -eq 'show') {
    [M]::mouse_event(2, 0, 0, 0, 0); Start-Sleep -Milliseconds 50; [M]::mouse_event(4, 0, 0, 0, 0)
    Write-Output "left-clicked"
} else {
    [M]::mouse_event(8, 0, 0, 0, 0); Start-Sleep -Milliseconds 50; [M]::mouse_event(16, 0, 0, 0, 0)
    Start-Sleep -Milliseconds 800
    $mc = New-Object System.Windows.Automation.PropertyCondition([System.Windows.Automation.AutomationElement]::NameProperty, '終了')
    $item = $root.FindAll([System.Windows.Automation.TreeScope]::Descendants, $mc) |
        Where-Object { $_.Current.ControlType -eq [System.Windows.Automation.ControlType]::MenuItem } | Select-Object -First 1
    if (-not $item) { Write-Output "menu item not found"; exit 3 }
    $mr = $item.Current.BoundingRectangle
    [M]::SetCursorPos([int]($mr.X + $mr.Width / 2), [int]($mr.Y + $mr.Height / 2)) | Out-Null
    Start-Sleep -Milliseconds 150
    [M]::mouse_event(2, 0, 0, 0, 0); Start-Sleep -Milliseconds 50; [M]::mouse_event(4, 0, 0, 0, 0)
    Write-Output "menu 終了 clicked at $($mr.X),$($mr.Y)"
}
