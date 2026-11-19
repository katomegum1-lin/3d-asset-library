# 技术决策记录（DECISIONS）

> 每条都写「为什么选 A 不选 B」。面试时被追问就靠这个文件。
> 规则：AI 给出方案后，自己用一句话写下理由。写不出理由的，就是没搞懂。

---

## D1 · 用 useExtendedLib 引入 XR-FRAME，而不是 npm 装 three.js

- **日期**：2026-11-19
- **决策**：`app.json` 里 `"useExtendedLib": {"xr-frame": true}`
- **备选**：npm 安装 three.js + 小程序适配层
- **理由**：
  1. XR-FRAME 是微信官方扩展库，不用自己维护适配层
  2. 不增加小程序包体（扩展库不计入主包 2MB 限制）
  3. 符合项目红线"不接 Three.js 移植版"
- **代价**：XR-FRAME 生态和文档不如 three.js 丰富，遇到问题资料少

---

## D2 · 相机控制用 `camera-orbit-control`，不手写 touch 事件

- **日期**：2026-11-19
- **决策**：`<xr-camera ... camera-orbit-control="" />`
- **备选**：监听 `touchstart/touchmove` 自己算旋转矩阵
- **理由**：官方组件已实现单指旋转 + 双指缩放，手写要处理惯性、边界、双指中心点，成本高且容易出 bug
- **注意**：属性名是 `camera-orbit-control`，不是 `camera-orbit-controller`（这个坑记一下）

---

## D3 · 不使用任何 glTF 几何压缩扩展（已实测验证）

- **日期**：2026-11-19
- **结论**：XR-FRAME **不支持** `KHR_draco_mesh_compression`，也**不支持** `EXT_meshopt_compression`
- **验证方法**：同一个 DamagedHelmet 模型产出三个版本，上传 COS 后在小程序里逐个加载

  | 版本 | 体积 | 依赖扩展 | 实测结果 |
  |---|---|---|---|
  | helmet-safe | 1.18 MB | 无 | ✅ 正常显示 |
  | helmet-meshopt | 0.83 MB | `EXT_meshopt_compression` | ❌ 黑屏 |
  | helmet-draco | 0.73 MB | `KHR_draco_mesh_compression` | ❌ 黑屏 |

- **决策**：优化流水线固定使用 `--compress false`，靠「贴图降采样 + 网格精简」控制体积
- **效果**：DamagedHelmet 3.60 MB → 1.18 MB（**-67%**），可直接使用
- **代价**：牺牲了约 0.45 MB 的额外压缩空间（12%），换取 100% 的机型兼容性
- **意义**：这个取舍有对照实验支撑，而不是凭感觉选

---

## D4 · models.json 远端优先 + 本地回退

- **日期**：2026-11-19
- **决策**：`loadModels()` 先请求远端，失败或数据异常时静默回退到本地 `assets/models.json`
- **理由**：
  1. M1/M2 阶段还没配 COS，也能立刻看到列表
  2. 真机弱网时不会白屏
  3. 面试演示时不依赖网络
- **代价**：需要维护两份数据，M4 之后要考虑同步

---

## D5 · gltf-transform 装在项目内（tools/），不全局安装

- **日期**：2026-11-19
- **决策**：`npm install --prefix tools`，用 `npx --yes @gltf-transform/cli`
- **理由**：全局安装会污染系统环境，换电脑要重装；项目内安装跟着项目走，`tools/node_modules` 不该提交到 git（已在 .gitignore 里排除）

---

## D6 · 用程序生成的立方体做首个测试模型

- **日期**：2026-11-19
- **决策**：`tools/make-cube-glb.mjs` 直接生成 1KB 的 cube.glb
- **理由**：在拿到真实模型之前，先把「小程序 → XR-FRAME → GLB → 渲染」这条链路跑通。链路问题和模型问题分开排查，否则出错了不知道是谁的锅

---

## D7 · 本地清单用 models.js，远端才用 models.json

- **日期**：2026-11-19
- **决策**：`assets/models.js` 用 `module.exports` 导出；远端 COS 上仍放 `models.json`
- **踩坑经过**：最初本地直接 `require('../../assets/models.json')`，导致整页白屏 —— 小程序模块系统**不支持 require .json 文件**，页面 JS 一加载就抛错，WXML 根本没机会渲染
- **理由**：远端走 `wx.request` 拿到的是字符串，`JSON.parse` 后同样是对象，两边结构可以完全一致
- **教训**：白屏 ≠ 样式问题。先看 Console，再看页面 JS 是否在加载阶段就抛错

---

## D8 · 稳定版开发者工具不支持 XR-FRAME 扩展库，改用开发版

- **日期**：2026-11-19
- **现象**：
  1. 预览（`cli preview`）报 `not found extended plugin! name = xr-frame`
  2. 模拟器里预览页永远停在"加载中"，`xr-scene` 的 `ready` 事件不触发
- **排查过程**（可复用的方法论）：
  1. **A/B 隔离**：临时去掉 `useExtendedLib` 再预览 → 成功（11.5KB）。加回去 → 失败。**证明根因在这一行，不在页面代码**
  2. **加自诊断**：页面 `onReady` 里 `this.selectComponent('#xr-scene')`，拿不到实例 → 说明标签根本没被注册
  3. **查官方 QA**：xr-frame-demo 仓库 FAQ 明确写"开发者工具无法使用 xr-frame → 下载最新的开发版工具"
- **结论**：稳定版 2.02.2609250 不具备 xr-frame 扩展库；官方建议用开发版（nightly）
- **决策**：改用开发版工具，与稳定版共存，项目目录不变
- **教训**：白屏/卡加载时，**先把"是谁的问题"隔离出来**（配置？代码？工具？），再动手修。这次如果直接去改 WXML，会白改一天

---

## D9 · 稳定版和开发版抢单实例锁，导致开发版"启动即退出"

- **日期**：2026-11-19
- **现象**：安装开发版后双击无任何反应；进程列表里始终只有稳定版；无报错、无弹窗、无崩溃日志
- **误判**：先后怀疑过 ①杀毒软件静默拦截 ②安装包不完整 ③环境变量 `ELECTRON_RUN_AS_NODE=1`
  - 实测：`Get-MpThreatDetection` 无记录；安装目录文件完整；用户/系统级环境变量均为空
- **破案关键**：**前台运行** exe 并看它自己打印什么
  ```
  [devtools] 已有运行中的实例，已唤起已有窗口，本次启动退出
  ```
  退出码 0 —— 不是崩溃，是**主动交接后退出**
- **根因**：稳定版和开发版共用单实例锁，稳定版开着时开发版启动会被"顶替"
- **解法**：先彻底关闭稳定版，再启动开发版；两者不能同时运行
- **方法论**：GUI 程序"点了没反应"时，**用命令行前台启动看 stdout**，别只盯着有没有窗口。退出码 0 + 无进程 = 主动退出，不是崩溃

---

## D10 · XR-FRAME 必须由 `renderer: "xr-frame"` 的自定义组件承载

- **日期**：2026-11-19
- **错误写法**（网上流传很广、AI 也爱这么写）：
  ```json
  // app.json
  "useExtendedLib": { "xr-frame": true }
  ```
  后果：预览上传报 `not found extended plugin! name = xr-frame`；`<xr-scene>` 在页面里不注册
- **正确写法**（官方《XR-Frame 指南》）：
  1. 建自定义组件，`index.json` 写 `{"component": true, "renderer": "xr-frame", "usingComponents": {}}`
  2. 组件 wxml 里放 `<xr-scene>`
  3. `app.json` 加 `"lazyCodeLoading": "requiredComponents"`
  4. 页面通过 `usingComponents` 引用该组件
- **要求**：基础库 ≥ 2.32.0
- **方法论教训**：
  - 遇到"组件未注册"时，**先查官方指南的"新建一个 XR 组件"章节**，不要相信搜索结果和模型记忆
  - 官方文档有 `.md` 版本（URL 末尾换 `.md`），比抓网页正文干净得多
  - 隔离实验（去掉配置看 A/B 结果）能快速排除变量，但不能代替查文档

---

## D11 · 性能埋点尝试失败并回滚

- **日期**：2026-11-19
- **目标**：记录 modelId、加载耗时、可交互耗时、机型
- **尝试过的三条路**：
  1. 组件 `triggerEvent` → 页面 `bind:xxx`：模拟器能收到，**真机收不到**
  2. 组件 `setData({ sceneReadyAt })` → 页面 `selectComponent` 轮询：**真机收不到**
  3. 组件写 `getApp().globalData.xrPerf` → 页面 `setInterval` 轮询：组件侧日志确认写入了，**页面侧仍读不到**
- **结论**：`renderer: "xr-frame"` 的组件与页面之间的回调通道存在阻断，具体原因未完全定位
- **决策**：回滚全部埋点代码，不保留半成品功能
- **简历措辞**：不写 P50/P90，改写「首屏可交互 < 1s」这类保守描述
- **教训**：**模拟器通过 ≠ 真机通过**。凡是依赖框架回调的指标，必须在真机上第一时间验证，不要先在模拟器里做完整实现

---

## 待记录的决策

- [ ] COS 还是 OSS？（看哪个有免费额度）
- [ ] 缩略图是模型渲染图还是 AI 生成？
- [ ] 三个 DCC 模型的制作顺序
- [ ] 是否要给模型加骨骼动画
