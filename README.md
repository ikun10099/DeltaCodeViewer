# 三角洲行动 · 改枪码库

三角洲行动（Delta Force）改枪码查看器，**Windows 桌面版（tkinter）+ Android 版（WebView 壳）** 双端实现。

数据源：

- 改枪码 `https://delta-code.cn/api/loadouts`
- 今日地图密码 `https://delta-code.cn/api/daily-password`

均为公开只读接口。

<img src="icon_512.png" width="120" alt="图标">

---

## 直接下载

前往 **[Releases](https://github.com/ikun10099/DeltaCodeViewer/releases/latest)** 页面下载，点开 `Assets` 即可：

| 平台 | 文件 | 大小 | 直链 |
|---|---|---|---|
| Windows 10/11 x64（免安装单文件） | `DeltaCodeViewer-portable-win64.exe` | 11.5 MB | [下载](https://github.com/ikun10099/DeltaCodeViewer/releases/latest/download/DeltaCodeViewer-portable-win64.exe) |
| Android 5.0+（arm64 / armv7 / x86_64 通用） | `DeltaCodeViewer-android.apk` | 161 KB | [下载](https://github.com/ikun10099/DeltaCodeViewer/releases/latest/download/DeltaCodeViewer-android.apk) |

SHA-256（v3.2）：

```
4C685C3A9D74B2258C44DC3892CA7979A58E834E621A437AB21B536495FBA12E  DeltaCodeViewer-portable-win64.exe
928469865101FFBBBC21ECE23A97D9B030F3ACBB6A274786E6EF0D50357597D1  DeltaCodeViewer-android.apk
```

> `releases/latest/download/<文件名>` 是 GitHub 的稳定直链，发新版后自动指向最新，不用改链接。
> exe 未做 Authenticode 签名，首次运行 SmartScreen 会提示「更多信息 → 仍要运行」。
> apk 使用自签名证书，安装时需允许「未知来源」。

---

## 功能

- **1342 条改枪码**全量分页拉取（12 页 × 120 条），本地缓存离线可读
- **今日地图密码**：六张地图每日动态密码（零号大坝 / 长弓溪谷 / 巴克什 / 航天基地 / 潮汐监狱 / AZ3），显示官方更新时间与本地拉取时刻，**每天 0 点后自动刷新**，只读展示
- **武器家族分类**：突击步枪 / 冲锋枪 / 射手步枪 / 狙击枪 / 轻机枪 / 霰弹枪 / 手枪 / 套装 / 特殊 / 其他
- **金枪客任务分类**：`tags / name / player / core / slug` 五字段联合判定，命中 29 条，带「阶段」列并按阶段排序
- **搜索**：武器 / 配装名 / 作者 / 改枪码 / 标签 全字段子串匹配
- **排序**：更新 / 造价 / 复制次数 / 阶段，可升降序
- **一键复制**改枪码到剪贴板
- **深色 / 浅色双主题**
- 单实例运行、原子写缓存（tmp + rename）、拉取失败自动回退缓存
- **429 退避重试**：服务端限流 60 次/分钟，撞限流时按 0.9s×(n+1) 递增等待后重试

---

## 目录结构

```
.
├── app.py                              # 桌面版全部逻辑（tkinter + Canvas 自绘）
├── selftest.py                         # 离线自检，62 项断言，不联网
├── index.spec                          # PyInstaller 打包配置
├── shot2.ps1                           # 截图脚本（DPI 感知 + DWM 阴影内缩）
├── icon.ico                            # 应用图标（7 档 256/128/64/48/32/24/16）
├── icon_512.png                        # 图标母版 512×512
├── dist/
│   ├── DeltaCodeViewer-portable-win64.exe
│   └── DeltaCodeViewer-android.apk
└── android/
    ├── build.ps1                       # aapt2 → javac → d8 → zipalign → apksigner
    ├── mkicon.py                       # 由 icon_512.png 生成 5 档 mipmap
    └── app/
        ├── AndroidManifest.xml         # cn.deltacode.loadout / minSdk 23 / targetSdk 34
        ├── assets/                     # index.html + style.css + app.js（H5 界面）
        ├── res/                        # values + mipmap-*
        └── src/cn/deltacode/loadout/
            └── MainActivity.java       # WebView 壳 + HTTPS 拉取 + JS 桥
```

---

## 桌面版

```powershell
# 需要 Python 3.12（Windows 官方安装包自带 tkinter）
python app.py

# 自检
python selftest.py
```

运行依赖仅标准库：`tkinter`、`urllib`、`json`、`threading`、`ctypes`、`ssl`。

打包：

```powershell
# 单文件版（首启解包到 %TEMP%\_MEI*，退出自删）
pyinstaller --noconfirm --clean --onefile --windowed `
  --name "三角洲改枪码库" --icon icon.ico --add-data "icon.ico;." --noupx app.py

# 目录版（冷启动快约 1.5s，不占 TEMP）
pyinstaller --noconfirm --clean --windowed `
  --name "三角洲改枪码库" --icon icon.ico --add-data "icon.ico;." --noupx app.py
```

> 不要加 `--runtime-tmpdir` 指向固定路径 —— 换机器 / 换用户名会因目录不存在直接启动失败。

### 今日地图密码卡片

- 布局：3 列 × 2 行网格，卡片式只读展示，不可点击复制
- 时间戳：`官方 HH:MM  ·  拉取 HH:MM:SS`，前者是服务端声明的更新时间，后者是本地实际拉取时刻
- 自动刷新：`_schedule_daily_tick()` 每 60 秒比对一次缓存日期与本地日期，跨天就触发拉取；不用超长 `after(ms)` 是因为休眠 / 时钟漂移会让长定时失准
- 缓存：`%LOCALAPPDATA%\DeltaCodeViewer\daily.json`，tmp + `os.replace` 原子写；拉取失败自动回退缓存并标注「⚠ 刷新失败，显示缓存」

---

## Android 版

不用 gradle、不用 Android Studio，纯命令行构建。需要：

- JDK 17
- Android SDK `build-tools;34.0.0` + `platforms;android-34`

```powershell
$env:ANDROID_SDK_ROOT = 'D:\android-sdk'
$env:JAVA_HOME        = 'C:\Program Files\Java\jdk-17'
cd android
.\build.ps1
# 产物：dist/DeltaCodeViewer-android.apk
```

首次构建需要签名库（脚本默认读 `android/keystore/deltacode.jks`）：

```powershell
keytool -genkeypair -v -keystore keystore\deltacode.jks -alias deltacode `
  -keyalg RSA -keysize 2048 -validity 10950 `
  -storepass deltacode2026 -keypass deltacode2026 `
  -dname "CN=DeltaCode Loadout, OU=App, O=DeltaCode, L=Hangzhou, ST=Zhejiang, C=CN"
```

构建流程：`aapt2 compile` → `aapt2 link`（`-A` 打包 assets）→ `javac` → `d8` → zip 合并 `classes.dex` → `zipalign -p -f 4` → `apksigner`（v1+v2+v3）。

Android 端实现要点：

- UI 是 `assets/` 里的 H5（HTML + CSS + 原生 JS，无框架），CSS 变量完整复刻桌面版 30 键调色板
- Java 侧负责 HTTPS 拉取（UA 必带，否则 CDN 403）与缓存，通过 `@JavascriptInterface` 桥 `Native` 暴露给页面：`loadCache / loadDaily / startDailyFetch / isFetching / copy / toast / appVersion`
- 分类与任务判定逻辑与 `app.py` 逐行对齐（`classify` 最长关键词优先、`matchQuest` 五字段、`questStep` 阶段正则）
- 今日密码卡片逻辑同样对齐：3×2 网格、`官方 … · 拉取 …`、每分钟 tick 跨天刷新
- 缓存写 `getFilesDir()/cache.json` 与 `getFilesDir()/daily.json`，tmp + rename 原子写
- 分页拉取后 `mergeWithCache()` 与旧缓存合并（新数据优先、旧条目补全），某页失败不会丢已有数据

---

## 数据结构

```jsonc
// Windows: %LOCALAPPDATA%\DeltaCodeViewer\cache.json
// Android: /data/data/cn.deltacode.loadout/files/cache.json
{
  "saved_at": "2026-11-12 23:49",
  "items": [
    {
      "id": "cl_MA1COBLAST",
      "weapon": "套装",
      "name": "麦扣Ma1co 黑潮爆破套装",
      "code": "Ma1co-BLAST6LIFQ6O04I54L1DBN87E3",
      "tags": ["黑潮爆破", "套装码", "主播同款"],
      "player": "麦扣Ma1co",
      "copy_times": 99,
      "collect_times": 1,
      "price": 0,
      "updatedAt": "2026-10-10"
    }
  ]
}
```

```jsonc
// daily.json
{
  "items": [
    { "name": "零号大坝", "code": "3248" },
    { "name": "长弓溪谷", "code": "7429" },
    { "name": "巴克什",   "code": "9510" },
    { "name": "航天基地", "code": "1980" },
    { "name": "潮汐监狱", "code": "2125" },
    { "name": "AZ3",      "code": "5182" }
  ],
  "date": "2026-11-21",
  "updatedText": "11-21 00:00",
  "isToday": true,
  "fetchedAt": "00:53:07"
}
```

改枪码接口分页：`totalPages=12`、`pageSize=120`、`total=1342`。
今日密码接口不支持 `?date=` 参数，永远返回当天。

---

## 自检覆盖

`selftest.py` 62 项断言，全部离线：

- 分类规则：`MK47` 不被 `mk4` 误判为冲锋枪、`M7`/`M14` 区分、空武器名回落「其他」
- 任务判定：五字段任一命中、slug 随机串 `6JQKF4409` 不误命中、任务优先于武器家族
- 阶段解析：`金枪客1` → `1`、`金枪客6/7` → `6/7`、无阶段返回 `("", "")`
- 分桶守恒：全部条目 1342 == 各家族与任务求和
- 排序、格式化（`fmt` / `fmt_price` / `fmt_date`）

---

## 说明

- 接口返回 `trusted: false` —— 站点自行声明数据未经审核，使用前请自行判断。
- 请求必须同时带 `User-Agent` 与 `Accept-Language`，否则 CDN 返回 403；UA 含 `curl` / `python-requests` / `Java` / `okhttp` / `node-fetch` 等子串会被直接拒绝。
- 接口限流 60 次/分钟（响应头 `x-ratelimit-limit` / `x-ratelimit-remaining`），刷新过于频繁会拿到 429，两端都做了递增退避。
- 桌面版 Windows 10/11 x64 可用；PyInstaller 6.x bootloader 不再支持 Win7。
- Android 端 targetSdk 34、minSdk 23，已在 Android 15 x86_64 模拟器实测通过。

---

## License

个人学习用途，代码可自由参考。游戏内数据与改枪码版权归原作者与游戏方所有。
