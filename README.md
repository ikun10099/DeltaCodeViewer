# 三角洲行动 · 改枪码库

三角洲行动（Delta Force）改枪码查看器，桌面版（Windows / tkinter）与 Android 版（WebView 壳）双端实现。
数据源：`https://delta-code.cn/api/loadouts`（只读，公开接口）。

![预览](icon_512.png)

---

## 功能

- **1342 条改枪码**全量分页拉取，本地缓存离线可读
- **武器家族分类**：突击步枪 / 冲锋枪 / 射手步枪 / 狙击枪 / 轻机枪 / 霰弹枪 / 手枪 / 套装 / 特殊
- **金枪客任务分类**：`tags / name / player / core / slug` 五字段联合判定，命中 29 条，附带「阶段」列并按阶段排序
- **搜索**：武器 / 配装名 / 作者 / 改枪码 / 标签 全字段子串匹配
- **排序**：更新 / 造价 / 复制次数 / 阶段，支持升降序
- **一键复制**改枪码到剪贴板
- **深色 / 浅色双主题**
- 单实例运行、原子写缓存、失败页自动回退缓存

---

## 目录

```
.
├── app.py              # 桌面版全部逻辑（tkinter + Canvas 自绘界面）
├── selftest.py         # 离线自检，62 项断言，不联网
├── index.spec          # PyInstaller 打包配置
├── shot2.ps1           # 截图脚本（DWM 阴影内缩 + DPI 感知）
├── icon.ico            # 应用图标（7 档：256/128/64/48/32/24/16）
└── icon_512.png        # 图标母版 512×512
```

---

## 运行

```powershell
# 需要 Python 3.12 + tkinter（Windows 官方安装包自带）
python app.py
```

依赖：仅标准库（`tkinter`、`urllib`、`json`、`threading`、`ctypes`、`ssl`）。
打包用 `pyinstaller`，非运行必需。

---

## 自检

```powershell
python selftest.py
```

覆盖：分类规则（含 `MK47` 不被 `mk4` 误判）、任务判定（含 slug 随机串不误命中）、阶段解析、分桶守恒（1342 == 1342）、排序、格式化函数。

---

## 打包

```powershell
# 单文件版（首次启动解包到 %TEMP%\_MEI*，退出自删）
pyinstaller --noconfirm --clean --onefile --windowed `
  --name "三角洲改枪码库" --icon icon.ico --add-data "icon.ico;." --noupx app.py

# 目录版（冷启动快，不占 TEMP）
pyinstaller --noconfirm --clean --windowed `
  --name "三角洲改枪码库" --icon icon.ico --add-data "icon.ico;." --noupx app.py
```

> 不要加 `--runtime-tmpdir` 指向固定路径：换机器 / 换用户名会因目录不存在而启动失败。

---

## 数据结构

```jsonc
// %LOCALAPPDATA%\DeltaCodeViewer\cache.json
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

接口分页：`totalPages=12`、`pageSize=120`、`total=1342`。

---

## 说明

- 接口返回 `trusted: false`，即数据由站点自行声明为未经审核，使用前请自行判断。
- 请求必须带 `User-Agent`，否则 CDN 返回 403。
- 桌面版无 Authenticode 签名，首次运行会触发 SmartScreen 提示。

---

## License

个人学习用途，代码可自由参考。游戏内数据与改枪码版权归原作者与游戏方所有。
