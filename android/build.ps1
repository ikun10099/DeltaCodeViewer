# ============================================================
#  三角洲改枪码库 · Android APK 手工构建脚本
#  aapt2 -> javac -> d8 -> zip merge -> zipalign -> apksigner
#
#  不依赖 gradle / Android Studio，只需要 sdk 的 build-tools + platforms。
#
#  用法：
#    $env:ANDROID_SDK_ROOT = 'D:\AI\android-build\sdk'
#    $env:JAVA_HOME        = 'C:\Program Files\Java\jdk-17'
#    .\build.ps1
#
#  可选参数：
#    -Sdk        SDK 根目录（默认取 $env:ANDROID_SDK_ROOT）
#    -BuildTools build-tools 版本号（默认 34.0.0）
#    -Keystore   签名库路径（默认 .\keystore\deltacode.jks）
#    -OutDir     产物目录（默认 .\dist）
# ============================================================
param(
    [string]$Sdk = $env:ANDROID_SDK_ROOT,
    [string]$BuildTools = '34.0.0',
    [string]$Keystore = '',
    [string]$OutDir = ''
)

$ErrorActionPreference = 'Stop'
$PROJ = $PSScriptRoot
if (-not $OutDir) { $OutDir = Join-Path $PROJ 'dist' }
if (-not $Keystore) { $Keystore = Join-Path $PROJ 'keystore\deltacode.jks' }

if (-not $Sdk) { throw '未指定 SDK：请设置 $env:ANDROID_SDK_ROOT 或用 -Sdk 传入' }
if (-not $env:JAVA_HOME) { throw '未指定 JDK：请设置 $env:JAVA_HOME（需要 JDK 17）' }

$BT       = Join-Path $Sdk "build-tools\$BuildTools"
$PLATFORM = Join-Path $Sdk 'platforms\android-34\android.jar'
$APPDIR   = Join-Path $PROJ 'app'
$OUT      = Join-Path $PROJ 'build'

$env:ANDROID_HOME = $Sdk

foreach ($p in @("$BT\aapt2.exe", "$BT\d8.bat", "$BT\apksigner.bat", "$BT\zipalign.exe", $PLATFORM, $Keystore)) {
    if (-not (Test-Path $p)) { throw "缺少构建依赖: $p" }
}

if (Test-Path $OUT) { Remove-Item $OUT -Recurse -Force }
foreach ($d in 'compiled', 'gen', 'classes', 'dex') { New-Item -ItemType Directory -Force -Path (Join-Path $OUT $d) | Out-Null }
New-Item -ItemType Directory -Force -Path $OutDir | Out-Null

function Step($n, $msg) { Write-Host "[$n] $msg" -ForegroundColor Cyan }

# ── 1. 编译资源 ───────────────────────────────────────────
Step '1/7' 'aapt2 compile'
& "$BT\aapt2.exe" compile --dir "$APPDIR\res" -o "$OUT\compiled"
if ($LASTEXITCODE -ne 0) { throw "aapt2 compile 失败 ($LASTEXITCODE)" }

# ── 2. 链接资源 + 打包 assets ─────────────────────────────
Step '2/7' 'aapt2 link'
& "$BT\aapt2.exe" link -o "$OUT\base.apk" `
    -I $PLATFORM `
    --manifest "$APPDIR\AndroidManifest.xml" `
    -A "$APPDIR\assets" `
    --java "$OUT\gen" `
    --min-sdk-version 23 --target-sdk-version 34 `
    --version-code 3 --version-name '3.0' `
    (Get-ChildItem "$OUT\compiled\*.flat" | ForEach-Object { $_.FullName })
if ($LASTEXITCODE -ne 0) { throw "aapt2 link 失败 ($LASTEXITCODE)" }

# ── 3. 编译 Java ──────────────────────────────────────────
Step '3/7' 'javac'
$javaFiles  = @(Get-ChildItem "$OUT\gen" -Recurse -Filter '*.java' | ForEach-Object { $_.FullName })
$javaFiles += @(Get-ChildItem "$APPDIR\src" -Recurse -Filter '*.java' | ForEach-Object { $_.FullName })
& "$env:JAVA_HOME\bin\javac.exe" -encoding UTF-8 -source 8 -target 8 `
    -bootclasspath $PLATFORM -classpath $PLATFORM `
    -d "$OUT\classes" $javaFiles 2>&1 |
    Where-Object { $_ -notmatch 'bootstrap class path|source value 8|target value 8|deprecat' }
if ($LASTEXITCODE -ne 0) { throw "javac 失败 ($LASTEXITCODE)" }

# ── 4. dex ────────────────────────────────────────────────
Step '4/7' 'd8'
$classFiles = @(Get-ChildItem "$OUT\classes" -Recurse -Filter '*.class' | ForEach-Object { $_.FullName })
$d8Args = ($classFiles | ForEach-Object { '"{0}"' -f $_ }) -join ' '
& cmd /c "`"$BT\d8.bat`" --release --min-api 23 --lib `"$PLATFORM`" --output `"$OUT\dex`" $d8Args"
if ($LASTEXITCODE -ne 0) { throw "d8 失败 ($LASTEXITCODE)" }
if (-not (Test-Path "$OUT\dex\classes.dex")) { throw 'd8 未产出 classes.dex' }

# ── 5. 把 classes.dex 写进 apk ────────────────────────────
Step '5/7' 'merge classes.dex'
Add-Type -AssemblyName System.IO.Compression.FileSystem
$zip = [System.IO.Compression.ZipFile]::Open("$OUT\base.apk", 'Update')
try {
    $old = $zip.GetEntry('classes.dex')
    if ($old) { $old.Delete() }
    [void][System.IO.Compression.ZipFileExtensions]::CreateEntryFromFile(
        $zip, "$OUT\dex\classes.dex", 'classes.dex', 'Optimal')
} finally { $zip.Dispose() }

# ── 6. zipalign ───────────────────────────────────────────
Step '6/7' 'zipalign'
if (Test-Path "$OUT\aligned.apk") { Remove-Item "$OUT\aligned.apk" -Force }
& "$BT\zipalign.exe" -p -f 4 "$OUT\base.apk" "$OUT\aligned.apk"
if ($LASTEXITCODE -ne 0) { throw "zipalign 失败 ($LASTEXITCODE)" }

# ── 7. 签名 ───────────────────────────────────────────────
Step '7/7' 'apksigner'
$apkOut = Join-Path $OutDir 'DeltaCodeViewer-android.apk'
if (Test-Path $apkOut) { Remove-Item $apkOut -Force }
& cmd /c "`"$BT\apksigner.bat`" sign --ks `"$Keystore`" --ks-pass pass:deltacode2026 --key-pass pass:deltacode2026 --ks-key-alias deltacode --v1-signing-enabled true --v2-signing-enabled true --v3-signing-enabled true --out `"$apkOut`" `"$OUT\aligned.apk`""
if ($LASTEXITCODE -ne 0) { throw "apksigner 失败 ($LASTEXITCODE)" }
if (-not (Test-Path $apkOut)) { throw '未产出已签名 APK' }

$f = Get-Item $apkOut
Write-Host ''
Write-Host 'BUILD OK' -ForegroundColor Green
Write-Host ("  {0}" -f $f.FullName)
Write-Host ("  {0:N0} bytes ({1:N2} MB)" -f $f.Length, ($f.Length / 1MB))
