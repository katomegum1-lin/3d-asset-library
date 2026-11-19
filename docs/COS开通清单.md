# 腾讯云 COS 开通清单（M3）

> 目标：把 GLB 和 models.json 放到 HTTPS 上，让小程序能从云端加载。
> 全程免费额度够用（新用户有 6 个月免费额度）。

---

## 第 1 步：注册与实名

1. 打开 https://cloud.tencent.com/ 注册（微信扫码即可）
2. 完成**个人实名认证**（要身份证 + 人脸，约 5 分钟）
3. 没实名的话 COS 用不了

---

## 第 2 步：创建存储桶

控制台 → 对象存储 COS → 存储桶列表 → **创建存储桶**

| 选项 | 填什么 | 为什么 |
|---|---|---|
| 名称 | 任意，如 `asset-demo-1300000000` | 后缀是 APPID，自动带 |
| 地域 | **广州**（ap-guangzhou） | 离你近，国内访问快 |
| 访问权限 | **公有读私有写** | 小程序要能直接下载，但不能被别人传 |
| 版本控制 | 关闭 | 用不上 |
| 服务端加密 | 关闭 | 用不上 |

> ⚠️ 选「私有读写」的话，小程序下载会 403。

---

## 第 3 步：上传文件

进入存储桶 → 文件列表 → 上传

```
assets/glb/cube.glb        →  上传到根目录或 /models/ 下
docs/models.json           →  上传到根目录
```

**目录结构建议**：
```
/
├── models.json
└── models/
    ├── cube.glb
    └── (以后的真实模型)
```

上传时建议设置：
- **Content-Type**：`.glb` 要设成 `model/gltf-binary`（COS 一般能自动识别，不行就手动改）
- **Cache-Control**：`max-age=31536000`（模型不会变，缓存一年）

---

## 第 4 步：拿到访问地址

存储桶 → 概览 → **访问域名**，形如：

```
https://asset-demo-1300000000.cos.ap-guangzhou.myqcloud.com
```

拼接后的模型地址：
```
https://asset-demo-1300000000.cos.ap-guangzhou.myqcloud.com/models/cube.glb
```

**先在浏览器里打开这个链接**：
- 能下载/能显示 = 通了
- 403 = 权限没设成「公有读」
- 404 = 路径不对

> 💡 COS 默认域名由腾讯云完成过备案，**可以直接填进小程序后台**，不用自己买域名再备案（能省 2-3 周）。

---

## 第 5 步：小程序后台配置合法域名

1. 打开 https://mp.weixin.qq.com/ → 登录
2. 左侧 **开发管理 → 开发设置 → 服务器域名**
3. 在 **downloadFile 合法域名** 里添加：
   ```
   https://asset-demo-1300000000.cos.ap-guangzhou.myqcloud.com
   ```
   注意：**只填域名，不带路径，结尾不要斜杠**
4. 保存

> `request` 合法域名也要加同一个域名（读 models.json 用的是 `wx.request`）。

---

## 第 6 步：改代码

### 6.1 改 `app.js`

```js
globalData: {
  modelsUrl: 'https://asset-demo-1300000000.cos.ap-guangzhou.myqcloud.com/models.json'
}
```

### 6.2 改 models.json

把 url 换成云端地址：

```json
{
  "version": 1,
  "models": [
    {
      "id": "cube-demo",
      "name": "测试立方体",
      "source": "程序生成",
      "url": "https://asset-demo-1300000000.cos.ap-guangzhou.myqcloud.com/models/cube.glb",
      "thumbnail": "",
      "sizeText": "1.5 KB"
    }
  ]
}
```

### 6.3 本地也留一份

`assets/models.js` 保持本地路径作为兜底（断网时还能用）。

---

## 第 7 步：验证

1. 开发者工具里点「编译」
2. 首页列表应该从**远端**读到数据
3. 进预览页，模型从 HTTPS 加载
4. 手机预览再验一次（**真机才真正校验域名**）

---

## 排查表

| 现象 | 原因 | 解决 |
|---|---|---|
| 列表回退到本地（顶部黄条提示"远端请求失败"） | 域名没配 / 网络 | 检查合法域名，开发时先勾「不校验合法域名」 |
| 模型 403 | 存储桶权限是私有 | 改成「公有读私有写」 |
| 模型黑屏 | Content-Type 不对 | 改成 `model/gltf-binary` |
| 真机能读到列表但模型不出来 | 模型域名没加进 downloadFile | 两个域名都要加 |
| 页面报 `url not in domain list` | 合法域名缺了 | 按提示补上 |

---

## 成本

- 新用户：50GB 存储 + 每月 20GB 流量，**6 个月免费**
- 你的 Demo 总共不到 20MB，完全可以忽略
- 记得到期前删掉，或者直接不管（欠费也不会影响你的简历）
