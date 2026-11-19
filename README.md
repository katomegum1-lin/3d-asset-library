# 三维资产库预览小程序

面向移动端的三维资产库预览与分享工具。基于微信原生小程序 + XR-FRAME，
从云端加载 GLB 模型，支持手势旋转缩放、带参分享、本地文件预览和多主题切换。

> 个人项目 · 未上线 Demo 

---

## 成果数据

| 指标 | 数值 |
|---|---|
| 模型体积优化 | **3.60 MB → 1.18 MB（-67%）** |
| 主包体积 | **83 KB**（上限 2 MB） |
| 压缩方案选型 | 通过 3 组对照实验确定，见 `docs/DECISIONS.md` D3 |
| 验证覆盖 | 微信开发者工具模拟器 + Android 真机（vivo V2463A） |

---

## 功能

- **资产列表**：从云端 `models.json` 读取，失败自动回退本地清单
- **3D 预览**：XR-FRAME 加载 GLB，单指旋转 / 双指缩放
- **分享**：分享链接携带模型信息，好友点开加载同一模型
- **本地预览**：从微信聊天记录选择 `.glb` 文件，直接在本机查看（不上传服务器）
- **多主题**：暗夜 / 暖白 / 森林，3D 场景清屏色同步切换
- **登录页**：微信头像 + 昵称，仅保存在本机

---

## 目录结构

```
3D资产库小程序/
├── app.js / app.json / app.wxss
├── project.config.json          含 packOptions.ignore，排除非代码目录
├── pages/
│   ├── index/                   资产列表（主题、登录入口、本地导入）
│   ├── preview/                 3D 预览（XR-FRAME 渲染 + 分享）
│   └── login/                   登录页（本地存储，无后端）
├── components/
│   └── xr-view/                 ★ 带 renderer: xr-frame 的渲染组件
├── utils/
│   └── theme.js                 主题配置
├── assets/
│   ├── models.js                本地清单（require 不支持 .json）
│   └── glb/cube.glb             测试用立方体
├── tools/                       ⚠️ 不参与打包
│   ├── optimize.bat             一键优化 GLB（拖拽即可）
│   └── make-cube-glb.mjs        生成测试立方体
├── docs/                        ⚠️ 不参与打包
│   ├── DECISIONS.md             技术决策记录（含 10 条踩坑）
│   ├── XR-FRAME-API速查.md      API 速查，可直接喂给 AI
│   ├── 三个模型制作任务单.md     跨 DCC 导出规范
│   └── COS开通清单.md           云存储配置步骤
└── cloud-upload/                ⚠️ 不参与打包
    ├── models.json              上传到 COS 的清单
    └── models/                  优化后的 GLB
```

---

## 关键技术点

### 1. XR-FRAME 的接入方式

`<xr-scene>` **不能直接写在页面里**。必须放在一个 `index.json` 声明了
`"renderer": "xr-frame"` 的自定义组件中：

```json
{
  "component": true,
  "renderer": "xr-frame",
  "usingComponents": {}
}
```

同时 `app.json` 需要 `"lazyCodeLoading": "requiredComponents"`。

> 网上流传的 `"useExtendedLib": { "xr-frame": true }` 是错误写法，
> 会导致预览报 `not found extended plugin`，且组件不注册。

### 2. 模型优化流水线

```
DCC 导出 → gltf-transform optimize --compress false --texture-size 1024 → 上传 COS
```

**必须加 `--compress false`**：实测 XR-FRAME 不支持
`KHR_draco_mesh_compression` 和 `EXT_meshopt_compression`，
而 `gltf-transform optimize` 默认会加 meshopt，不加参数就会踩雷。

### 3. 分享链路的特殊处理

分享链接指向**首页**而不是预览页，由首页在 `onReady` 里 `navigateTo` 跳转。
原因：预览页作为小程序启动页时，XR-FRAME 渲染器尚未初始化，场景无法创建。

---

## 已知限制

| 限制 | 说明 |
|---|---|
| **PC 版微信不支持 3D** | 桌面端小程序容器无法渲染 XR-FRAME 场景，必须在手机上验证 |
| 不支持 Draco / meshopt | 见上方实测结论 |
| 本地预览仅支持 `.glb` | `.gltf` 依赖外部资源文件，微信无法一并读取 |
| 未发布 | 他人查看需先加入「体验成员」；发布需完成 ICP 备案 |

---

## 本地运行

见 `快速开始.md`。

**注意**：开发者工具必须使用**开发版**（nightly），稳定版不支持 XR-FRAME。
稳定版与开发版共用单实例锁，不能同时运行。

---

## 其他人如何使用这个项目

本项目采用 **MIT 协议**，任何人可以自由克隆、学习、修改、商用，无需授权。

### 直接体验

1. 用微信开发者工具（**开发版**）导入本目录
2. 填入自己的 AppID（没有可用测试号）
3. 直接编译即可看到列表页与 3D 预览
4. 本地兜底清单会加载 `assets/glb/cube.glb`，无需配置云端

### 换成自己的模型

1. 把自己的 `.glb` 放进 `cloud-upload/models/`
2. 运行 `cd tools && node precheck.mjs --base <你的COS域名>`
   脚本会校验文件并生成 `models.generated.json`
3. 检查无误后重命名为 `models.json`，上传到自己的 COS
4. 修改 `app.js` 里的 `modelsUrl` 指向你的云端地址
5. 在小程序后台配置 request + downloadFile 合法域名

### 你需要自备的东西

| 项目 | 说明 |
|---|---|
| 小程序 AppID | 免费注册，个人主体即可 |
| 腾讯云 COS 或阿里云 OSS | 有免费额度，配置步骤见 `docs/COS开通清单.md` |
| 模型文件 | 项目内自带的 `helmet-safe.glb` 来自 Khronos 官方示例（CC0） |

### 已知不支持的情况

- `KHR_draco_mesh_compression` / `EXT_meshopt_compression`（见 `docs/DECISIONS.md` D3）
- FBX / OBJ / STL 等制作格式，需先转换为 GLB
- 电脑版微信小程序容器（不支持 XR-FRAME 渲染，必须用手机）

---

## 贡献

欢迎提 Issue 或 PR。提交前请先跑一遍 `tools/precheck.mjs`，确保模型文件符合校验规则。

---

## 开发记录

`docs/DECISIONS.md` 记录了 10 条关键决策与踩坑过程，包括：

- D3：通过对照实验测出 XR-FRAME 不支持几何压缩扩展
- D7：小程序 `require` 不支持 `.json`
- D8：稳定版工具不支持 XR-FRAME
- D9：两个版本抢单实例锁导致"启动即退出"
- D10：XR-FRAME 必须由 `renderer: xr-frame` 的组件承载
