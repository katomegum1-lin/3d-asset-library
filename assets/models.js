/**
 * 本地兜底模型清单。
 *
 * 为什么用 .js 而不是 .json：
 * 小程序的 require 只支持 .js 模块，不支持直接 require .json 文件，
 * 否则页面 JS 会在加载阶段直接报错、整页白屏。
 *
 * 远端仍然读 models.json（格式完全一致），这里的结构要跟它保持一致。
 */
module.exports = {
  version: 1,
  updatedAt: '2026-11-19',
  models: [
    {
      id: 'cube-demo',
      name: '测试立方体',
      source: '程序生成（占位素材）',
      url: '/assets/glb/cube.glb',
      thumbnail: '',
      sizeText: '1.5 KB',
      note: '用于验证 XR-FRAME 加载链路。M3 时把 url 换成 COS 的 https 地址。'
    }
  ]
}
