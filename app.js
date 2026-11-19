App({
  globalData: {
    /**
     * 远端 models.json 地址。
     * M1/M2 阶段留空，走本地 assets/models.json；
     * M3 阶段填成 COS 的 https 地址，例如：
     * https://your-bucket-1250000000.cos.ap-guangzhou.myqcloud.com/models.json
     */
    modelsUrl: 'https://asset-demo-1536405020.cos.ap-guangzhou.myqcloud.com/models.json',
    // 列表页加载成功后缓存到这里，供预览页复用
    models: []
  },

  onLaunch() {
    console.log('[app] launch, XR-FRAME 扩展库已启用')
  }
})
