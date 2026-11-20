# Asset Forge — 资产转换工作台

一个把 3D 模型批量转成 **FBX / GLB** 的桌面小工具。本来是一堆 `.bat` 和 `.py` 脚本，
现在打包成一个窗口：拖文件夹进去、点开始、看进度。

## 启动

双击 **`启动 Asset Forge.bat`**。

首次启动会自动找本机的 Maya 和 Blender。找不到就在右上角 **⚙ 设置** 里手动指定：

| 程序 | 作用 | 本机路径 |
|---|---|---|
| `mayapy.exe` | 把 `.ma` / `.mb` 转成 FBX | `F:\BaiduNetdiskDownload\Maya2022\bin\mayapy.exe` |
| `blender.exe` | 把 FBX / OBJ / STL / DAE 转成 GLB | `D:\Program Files\Blender Foundation\Blender 5.2\blender.exe` |

路径只需设置一次，存在同目录的 `config.json` 里。

## 用法

1. 把文件夹**拖进窗口**（或点「📁 选择文件夹」）
2. 勾选要输出什么：`FBX` / `GLB` / `GLB 优化`
3. 确认输出目录（默认在源文件夹下的 `converted`）
4. 点「开始转换」

支持的输入格式：

- `.ma` `.mb` —— 走 Maya
- `.fbx` `.obj` `.stl` `.dae` `.glb` `.gltf` —— 走 Blender

## 输出结构

```
输出目录/
├── fbx/            导出的 FBX（勾选 FBX 时）
├── glb/            转换好的 GLB（勾选 GLB 时）
├── optimized/      优化后的 GLB（勾选优化时）
├── _maya_manifest.json
└── _glb_manifest.json
```

**不会覆盖已有文件**：重名时自动加 `_1`、`_2` 后缀。

## 勾选「GLB 优化」会做什么

调用 `@gltf-transform/cli`，减面 + 贴图降采样到 1024。
**强制 `--compress false`** —— 微信 XR-FRAME 不支持 Draco / meshopt，压缩过的 GLB 在真机上加载会失败。

优化需要 `tools/node_modules` 存在，否则自动跳过并提示。

## 目录结构

```
asset-forge/
├── asset-forge.py          主程序（界面 + 流水线调度）
├── engine/
│   ├── maya_export.py      Maya 引擎（由 mayapy.exe 执行）
│   └── blender_convert.py  Blender 引擎（由 blender.exe -b 执行）
├── 启动 Asset Forge.bat
├── config.json             自动生成，存路径配置
└── README.md
```

两个引擎和界面之间用行协议通信，界面据此更新进度条和每一行的状态：

```
##PROGRESS|当前|总数|文件名
##DONE|文件名|ok或fail|体积KB或面数|备注
##FINISH|成功数|总数
```

## 踩过的坑（改代码前先看这里）

### 1. MEL 的 `python()` 参数是代码，不是文件路径

```mel
python("C:/path/to/script.py");        // ✗ 把路径当 Python 代码编译 → invalid syntax
python("exec(open(r'C:/path/to/script.py').read())");   // ✓
```

### 2. 别用 `mayabatch -command`，用 `mayapy` 直接跑脚本

`mayabatch` 执行完或出错后**不会退出**，会一直挂着占 1.4 GB 内存，看起来就像"启动很慢"。
`mayapy.exe` 是标准 Python 解释器，脚本跑完自然退出。

### 3. `cmds.file(type="FBX export")` 在 mayapy 下不生成文件

必须用 FBX 插件命令：

```python
cmds.FBXExport("-f", dst)      # ✓ 整个场景
cmds.FBXExport("-f", dst, "-s")  # ✗ -s = 只导出选中物体；没选就导出空场景
```

### 4. `cmds.sets()` 在 Maya 2022 里是 `empty=True`

旧版的 `emptyValue=True` 会报 `TypeError: 标志"emptyValue"无效`。

### 5. 保存 .ma 要先 rename 再 save

```python
cmds.file(rename=path)
cmds.file(save=True, type="mayaAscii", force=True)
```

### 6. 中文路径

清单文件用 UTF-8 JSON 传参，`PYTHONIOENCODING=utf-8` + `PYTHONUNBUFFERED=1` 保证子进程输出不乱码、不缓冲。

## 已知限制

- 拖拽功能依赖 `tkinterdnd2`（`pip install tkinterdnd2`）。没装也能用，只是要手动点按钮选文件夹。
- 转 GLB 的 Blender 版本较新（5.2），导入操作符如果改名，`engine/blender_convert.py` 里的 `IMPORTERS` 表可能需要补一条。
- 未勾选 FBX 时，中间产物会放在输出目录的 `_fbx_temp/`，方便排查，不会自动删除。
