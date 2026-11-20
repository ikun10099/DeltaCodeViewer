param(
  [string]$Out = "D:\AI\beautify\shot.png",
  [int]$ClickX = -1,
  [int]$ClickY = -1,
  [switch]$Full,
  [switch]$After
)
Add-Type -AssemblyName System.Drawing
Add-Type @"
using System;
using System.Runtime.InteropServices;
public class Dpi3 {
  [DllImport("user32.dll")] public static extern bool SetProcessDpiAwarenessContext(IntPtr c);
  [DllImport("user32.dll")] public static extern bool SetProcessDPIAware();
}
public class Win3 {
  [DllImport("user32.dll")] public static extern bool GetWindowRect(IntPtr h, out RECT r);
  [DllImport("user32.dll")] public static extern bool SetForegroundWindow(IntPtr h);
  [DllImport("user32.dll")] public static extern bool ShowWindow(IntPtr h, int c);
  [DllImport("user32.dll")] public static extern bool SetWindowPos(IntPtr h, IntPtr a, int x, int y, int cx, int cy, uint f);
  [DllImport("user32.dll")] public static extern bool BringWindowToTop(IntPtr h);
  [DllImport("user32.dll")] public static extern bool SetCursorPos(int x, int y);
  [DllImport("user32.dll")] public static extern void mouse_event(uint f, int dx, int dy, uint d, IntPtr e);
  [DllImport("user32.dll")] public static extern int GetSystemMetrics(int i);
  [StructLayout(LayoutKind.Sequential)] public struct RECT { public int L,T,R,B; }
}
"@
try { [Dpi3]::SetProcessDpiAwarenessContext([IntPtr](-4)) | Out-Null } catch { try { [Dpi3]::SetProcessDPIAware() | Out-Null } catch {} }

$p = Get-Process | Where-Object { $_.MainWindowTitle -like "*三角洲*" } | Select-Object -First 1
if (-not $p) { Write-Output "NO_WINDOW"; exit 1 }
$h = $p.MainWindowHandle
[Win3]::ShowWindow($h, 9) | Out-Null
[Win3]::SetWindowPos($h, [IntPtr](-1), 0,0,0,0, 0x0001 -bor 0x0002 -bor 0x0040) | Out-Null
[Win3]::BringWindowToTop($h) | Out-Null
[Win3]::SetForegroundWindow($h) | Out-Null
Start-Sleep -Milliseconds 800

$r = New-Object Win3+RECT
[Win3]::GetWindowRect($h, [ref]$r) | Out-Null

if ($ClickX -ge 0) {
  $ax = $r.L + $ClickX
  $ay = $r.T + $ClickY
  [Win3]::SetCursorPos($ax, $ay) | Out-Null
  Start-Sleep -Milliseconds 250
  [Win3]::mouse_event(0x0002, 0, 0, 0, [IntPtr]::Zero)
  Start-Sleep -Milliseconds 60
  [Win3]::mouse_event(0x0004, 0, 0, 0, [IntPtr]::Zero)
  Write-Output "CLICK $ax,$ay"
  Start-Sleep -Milliseconds 900
}

$bmp = New-Object System.Drawing.Bitmap ($r.R-$r.L-16), ($r.B-$r.T-16)
$g = [System.Drawing.Graphics]::FromImage($bmp)
$g.CopyFromScreen(($r.L+8), ($r.T+8), 0, 0, $bmp.Size)
$bmp.Save($Out, [System.Drawing.Imaging.ImageFormat]::Png)
$g.Dispose(); $bmp.Dispose()
if (-not $After) {
  [Win3]::SetWindowPos($h, [IntPtr](-2), 0,0,0,0, 0x0001 -bor 0x0002 -bor 0x0040) | Out-Null
}
Write-Output "SAVED $Out"
