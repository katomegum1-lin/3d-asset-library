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
  version: 4,
  updatedAt: '2026-11-19',
  models: [
    {
      id: 'cube-demo',
      name: '测试立方体',
      source: '程序生成',
      url: '/assets/glb/cube.glb',
      thumbnail: '',
      sizeText: '1.5 KB',
      note: '本地占位模型',
      stats: { vertices: 24, triangles: 12, maxTextureSize: 0 }
    }
  ]
}
