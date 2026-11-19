// 3D 预览页：根据 id 或分享参数取出模型地址，交给 XR-FRAME 渲染
//
// 进入方式：
//  1. 列表页跳转 —— 链接里带 url
//  2. 分享卡片 —— 分享链接里带 url 和 name
//  3. 本地导入 —— local=1，url 是微信临时文件路径
//
// 关键：<xr-scene> 必须在页面首次渲染时就拿到有效地址，
// 否则场景创建不出来（异步补地址是无效的）。
const MODELS = require('../../assets/models')
const { getTheme, toStyleVars, applyNavBar } = require('../../utils/theme')

Page({
  data: {
    modelUrl: '',
    modelName: '',
    loading: true,
    err: '',
    viewW: 0,
    viewH: 0,
    clearColor: '0.06 0.07 0.09 1',
    styleVars: '',
    isLocal: false
  },

  onLoad(query) {
    this.modelId = query.id || ''

    const info = wx.getSystemInfoSync()
    this.setData({ viewW: info.windowWidth, viewH: info.windowHeight })

    const theme = getTheme()
    this.setData({
      styleVars: toStyleVars(theme),
      clearColor: theme.clear
    })
    applyNavBar(theme)

    // ① 链接里直接带着地址（列表跳转 / 分享卡片 / 本地文件）
    if (query.url) {
      const url = decodeURIComponent(query.url)
      const name = query.name ? decodeURIComponent(query.name) : '三维模型'
      this.applyDirect(url, name, query.local === '1')
      return
    }

    // ② 用列表页缓存
    const cached = getApp().globalData.models
    if (cached && cached.length) {
      this.applyModel(cached)
      return
    }

    // ③ 兜底：自己拉云端清单
    this.loadModelsFromCloud()
  },

  applyDirect(url, name, isLocal) {
    this.setData({ modelUrl: url, modelName: name, isLocal: !!isLocal })
    wx.setNavigationBarTitle({ title: name })
  },

  loadModelsFromCloud() {
    const url = getApp().globalData.modelsUrl

    if (!url) {
      this.applyModel(MODELS.models || [])
      return
    }

    wx.request({
      url,
      timeout: 8000,
      success: (res) => {
        const list = res.data && res.data.models
        if (res.statusCode === 200 && Array.isArray(list) && list.length) {
          getApp().globalData.models = list
          this.applyModel(list)
        } else {
          this.applyModel(MODELS.models || [])
        }
      },
      fail: () => this.applyModel(MODELS.models || [])
    })
  },

  applyModel(list) {
    const hit = list.find((m) => m.id === this.modelId) || list[0]

    if (!hit || !hit.url) {
      this.setData({ loading: false, err: '没有找到对应的模型' })
      return
    }

    this.modelId = hit.id
    this.setData({ modelUrl: hit.url, modelName: hit.name })
    wx.setNavigationBarTitle({ title: hit.name })
  },

  onReady() {
    // 兜底：12 秒还没就绪就撤掉遮罩，避免永远卡在"加载中"
    setTimeout(() => {
      if (this.data.loading) this.setData({ loading: false })
    }, 12000)
  },

  handleAssetsLoaded() {},

  handleReady({ detail }) {
    // detail.value 是场景实例，后续要做播放动画、换材质都从这里拿
    this.scene = detail && detail.value
    this.setData({ loading: false })
  },

  onShareAppMessage() {
    // 本地文件没法分享给他人，只分享当前模型信息
    if (this.data.isLocal) {
      return {
        title: '三维资产库',
        path: '/pages/index/index'
      }
    }

    // 分享链接指向首页：预览页作为启动页时 xr-frame 渲染器还没初始化，
    // 走「首页 → navigateTo 预览页」这条路才能正常渲染。
    const parts = [`id=${this.modelId || ''}`]
    if (this.data.modelUrl) parts.push(`url=${encodeURIComponent(this.data.modelUrl)}`)
    if (this.data.modelName) parts.push(`name=${encodeURIComponent(this.data.modelName)}`)

    return {
      title: this.data.modelName || '三维资产预览',
      path: `/pages/index/index?${parts.join('&')}`
    }
  }
})
