# XR-FRAME API 速查（喂给 AI 之前先给它看这个）

> 整理日期：2026-11-19
> 来源：微信开放文档 · XR-Frame 章节（2026-10-22 更新）
> **用途：复制本文件内容给 GPT / Claude，能大幅降低它瞎编 API 的概率。**

---

## 1. 怎么引入（关键，最容易搞错）

> ⚠️ **2026-11-19 更正**：`useExtendedLib: {"xr-frame": true}` 是**错误写法**，
> 会导致预览上传报 `not found extended plugin! name = xr-frame`，
> 且 `<xr-scene>` 不会被注册。官方指南里根本没有这条配置。

正确做法：`<xr-scene>` 必须写在**自定义组件**里，该组件的 `index.json` 指定渲染器：

```json
{
  "component": true,
  "renderer": "xr-frame",
  "usingComponents": {}
}
```

同时在 `app.json` 加一行：

```json
{
  "lazyCodeLoading": "requiredComponents"
}
```

然后在页面里引用这个组件即可（见 `components/xr-view/`）。

基础库要求：`xr-frame` 从 **v2.32.0** 开始正式稳定。

---

## 2. 最小可用结构

```xml
<xr-scene bind:ready="handleReady">
  <xr-assets>
    <xr-asset-load type="gltf" asset-id="model" src="/assets/glb/cube.glb" />
  </xr-assets>

  <xr-node node-id="root">
    <xr-gltf model="model" />
  </xr-node>

  <xr-camera
    position="0 1.2 4"
    target="root"
    clear-color="0.06 0.07 0.09 1"
    camera-orbit-control=""
  />

  <xr-light type="ambient" color="1 1 1" intensity="0.9" />
  <xr-light type="directional" rotation="45 60 0" color="1 1 1" intensity="2.2" />
</xr-scene>
```

对应 JS：

```js
handleReady({ detail }) {
  this.scene = detail.value   // 场景实例，后续操作都从这里拿
}
```

---

## 3. 元素速查

| 标签 | 作用 | 关键属性 |
|---|---|---|
| `<xr-scene>` | 场景根节点 | `bind:ready`（初始化完成）、`bind:tick`（每帧） |
| `<xr-assets>` | 资源容器 | 里面放 `xr-asset-load` |
| `<xr-asset-load>` | 加载资源 | `type="gltf"`（必须是这个值）、`asset-id`、`src` |
| `<xr-node>` | 节点容器 | `node-id`（供 camera 的 target 引用）、`position`、`rotation`、`scale` |
| `<xr-gltf>` | 渲染 glTF/GLB | `model="asset-id"` |
| `<xr-camera>` | 相机 | `position`、`target`、`clear-color`、`camera-orbit-control` |
| `<xr-light>` | 灯光 | `type="ambient\|directional"`、`color`、`intensity`、`rotation` |

---

## 4. ⚠️ 三个已踩过的坑

### 坑 1：属性名是 `camera-orbit-control`，不是 `camera-orbit-controller`
官方"相机"文档原文示例：

```xml
<xr-camera position="0 1 4" clear-color="0.4 0.6 0.7 1"
           background="skybox" target="target" camera-orbit-control="" />
```

（来源：XR-Frame/组件/渲染/相机 Camera）

这个组件自带**单指旋转 + 双指缩放**，不用自己写 touch 事件。

### 坑 2：`xr-asset-load` 的 `type` 必须是 `"gltf"`
`.glb` 和 `.gltf` 都用 `type="gltf"`，靠文件后缀区分。
如果 src 是 `.gltf`（非 glb），**附属的贴图/缓冲文件必须放在同一路径、保持原来的相对结构**。

### 坑 3：加载不是一个请求就完事
官方说明 Loader 分三步：
1. 解析 `.gltf` / `.glb` 数据
2. 下载所有附属资源
3. 把模型数据重新拼成 xr-frame 渲染数据

**三步全完成才算加载完** —— 所以大模型会明显卡一下，必须有 loading 态。

---

## 5. 已实测的结论（2026-11-19）

| 项 | 结果 | 依据 |
|---|---|---|
| **KHR_draco_mesh_compression** | ❌ **不支持** | 同一模型 Draco 版加载黑屏，无压缩版正常 |
| **EXT_meshopt_compression** | ❌ **不支持** | 同上 |
| **KHR_mesh_quantization** | ❓ 单独未测 | 它总跟 meshopt 一起出现，建议一并避开 |
| 无扩展的标准 GLB | ✅ 支持 | 对照组正常显示 |

**结论：优化时必须 `--compress false`。** 体积靠「贴图降采样 + 网格精简」控制，实测能把 3.6MB 压到 1.18MB（-67%）。

**教训**：`gltf-transform optimize` 的默认行为会加 meshopt 压缩，**不加参数就会踩雷**，必须显式关掉。

---

## 6. 文档地址（旧链接已失效，用这些）

- 概述：https://developers.weixin.qq.com/miniprogram/dev/reference/xr-frame/component/overview/index.html
- GLTF 入门：https://developers.weixin.qq.com/miniprogram/dev/reference/xr-frame/component/gltf/introduction.html
- GLTF 使用说明（限制章节在这里）：https://developers.weixin.qq.com/miniprogram/dev/reference/xr-frame/component/gltf/specification.html
- 相机：https://developers.weixin.qq.com/miniprogram/dev/reference/xr-frame/component/render/camera.html

> 注意：官方文档每页右上角有「复制给 LLM」和「查看 Markdown」按钮 —— 直接把 Markdown 版贴给 AI，比贴网页正文效果好得多。

---

## 7. 给 AI 的提示词模板

```
你在帮我写微信小程序 XR-FRAME 代码。以下是官方 API 摘要，请严格按它写，
不要使用任何未在摘要中出现的属性名或标签：

【贴本文件第 2、3 节的表格和代码】

需求：<你的具体需求>
约束：
- 不用 three.js，不用 npm 包
- 只允许使用上面列出的 xr-* 标签和属性
- 如果某个 API 摘要里没有，请直接说"文档未覆盖"，不要猜
```
