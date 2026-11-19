// 资产列表页：远端 models.json + 本地导入的模型
// 注意：本地清单用 models.js，因为小程序 require 不支持 .json
const localModels = require('../../assets/models')
const { THEMES, getTheme, setTheme, toStyleVars, applyNavBar } = require('../../utils/theme')

const LOCAL_KEY = 'localModels'

Page({
  data: {
    models: [],
    loading: true,
    error: '',
    user: {},
    themeName: '',
    styleVars: ''
  },

  onLoad(query) {
    this.applyTheme(getTheme())
    this.loadUser()

    // 从分享卡片进入时先记下模型信息，等页面就绪后再跳转。
    // 在 onLoad 里直接 navigateTo 太早，页面栈还没准备好，预览页会渲染失败。
    if (query && query.url) {
      let rawUrl = query.url
      let rawName = query.name || ''
      try { rawUrl = decodeURIComponent(rawUrl) } catch (e) {}
      try { rawName = decodeURIComponent(rawName) } catch (e) {}

      this.pendingModel = { id: query.id || '', url: rawUrl, name: rawName }
      this.loadModels()
      return
    }

    // 首次进入引导登录（分享进入的不打扰）
    if (!wx.getStorageSync('userProfile') && !wx.getStorageSync('loginSkipped')) {
      wx.navigateTo({ url: '/pages/login/login' })
    }

    this.loadModels()
  },

  onShow() {
    this.loadUser()
    this.applyTheme(getTheme())
  },

  onReady() {
    if (!this.pendingModel) return

    const { id, url, name } = this.pendingModel
    this.pendingModel = null

    const parts = [`id=${id}`, `url=${encodeURIComponent(url)}`]
    if (name) parts.push(`name=${encodeURIComponent(name)}`)

    wx.navigateTo({ url: `/pages/preview/preview?${parts.join('&')}` })
  },

  onPullDownRefresh() {
    this.loadModels(() => wx.stopPullDownRefresh())
  },

  // ---------- 用户 & 主题 ----------

  loadUser() {
    this.setData({ user: wx.getStorageSync('userProfile') || {} })
  },

  applyTheme(theme) {
    this.setData({ themeName: theme.name, styleVars: toStyleVars(theme) })
    applyNavBar(theme)
  },

  onSwitchTheme() {
    const current = getTheme()
    wx.showActionSheet({
      itemList: THEMES.map((t) => t.name),
      success: (res) => {
        const picked = THEMES[res.tapIndex]
        if (!picked || picked.key === current.key) return
        setTheme(picked.key)
        this.applyTheme(picked)
      }
    })
  },

  goLogin() {
    wx.navigateTo({ url: '/pages/login/login' })
  },

  // ---------- 本地导入 ----------

  getLocalModels() {
    return wx.getStorageSync(LOCAL_KEY) || []
  },

  /** 合并「本地导入」+「远端/本地清单」，本地排前面 */
  refreshList(remoteList) {
    if (remoteList) this.remoteModels = remoteList
    const locals = this.getLocalModels()
    this.setData({ models: locals.concat(this.remoteModels || []) })
  },

  onImportLocal() {
    wx.chooseMessageFile({
      count: 1,
      type: 'file',
      extension: ['glb'],
      success: (res) => {
        const file = res.tempFiles && res.tempFiles[0]
        if (!file) return

        if (!/\.glb$/i.test(file.name || '')) {
          wx.showToast({ title: '只支持 .glb 文件', icon: 'none' })
          return
        }

        wx.showModal({
          title: '保存到资产库？',
          content: `「${file.name}」\n保存后会出现在列表里，可以随时删除`,
          confirmText: '保存',
          cancelText: '不保存',
          success: (r) => {
            if (r.confirm) this.saveLocalModel(file)
            else this.previewLocal(file.path, file.name)
          }
        })
      },
      fail: (err) => console.warn('[index] chooseMessageFile failed', err)
    })
  },

  saveLocalModel(file) {
    wx.showLoading({ title: '保存中', mask: true })
    wx.getFileSystemManager().saveFile({
      tempFilePath: file.path,
      success: (res) => {
        const locals = this.getLocalModels()
        locals.unshift({
          id: 'local-' + Date.now(),
          name: (file.name || '本地模型').replace(/\.glb$/i, ''),
          source: '本地导入',
          url: res.savedFilePath,
          thumbnail: '',
          sizeText: this.formatSize(file.size),
          isLocal: true
        })
        wx.setStorageSync(LOCAL_KEY, locals)

        wx.hideLoading()
        this.refreshList()
        wx.showToast({ title: '已保存', icon: 'success' })
      },
      fail: () => {
        wx.hideLoading()
        wx.showToast({ title: '保存失败', icon: 'none' })
      }
    })
  },

  formatSize(bytes) {
    if (!bytes) return ''
    if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(0) + ' KB'
    return (bytes / 1024 / 1024).toFixed(2) + ' MB'
  },

  previewLocal(path, name) {
    wx.navigateTo({
      url: `/pages/preview/preview?local=1` +
        `&url=${encodeURIComponent(path)}` +
        `&name=${encodeURIComponent(name)}`
    })
  },

  onDeleteLocal(e) {
    const id = e.currentTarget.dataset.id
    const locals = this.getLocalModels()
    const hit = locals.find((m) => m.id === id)
    if (!hit) return

    wx.showModal({
      title: '删除模型',
      content: `确定删除「${hit.name}」吗？`,
      confirmText: '删除',
      confirmColor: '#e34b4b',
      success: (res) => {
        if (!res.confirm) return

        if (hit.url) {
          wx.getFileSystemManager().removeSavedFile({
            filePath: hit.url,
            complete: () => {}
          })
        }

        wx.setStorageSync(LOCAL_KEY, locals.filter((m) => m.id !== id))
        this.refreshList()
        wx.showToast({ title: '已删除', icon: 'none' })
      }
    })
  },

  // ---------- 远端清单 ----------

  loadModels(done) {
    const remoteUrl = getApp().globalData.modelsUrl

    if (!remoteUrl) {
      this.useLocal()
      done && done()
      return
    }

    wx.request({
      url: remoteUrl,
      timeout: 8000,
      success: (res) => {
        const list = res.data && res.data.models
        if (res.statusCode === 200 && Array.isArray(list) && list.length) {
          getApp().globalData.models = list
          this.remoteModels = list
          this.setData({ loading: false, error: '' })
          this.refreshList()
        } else {
          this.useLocal('远端数据异常，已回退到本地模型')
        }
      },
      fail: (err) => {
        console.warn('[index] 远端 models.json 请求失败', err)
        this.useLocal('远端请求失败，已回退到本地模型')
      },
      complete: () => done && done()
    })
  },

  useLocal(warn) {
    const list = localModels.models || []
    getApp().globalData.models = list
    this.remoteModels = list
    this.setData({ loading: false, error: warn || '' })
    this.refreshList()
  },

  // ---------- 跳转 ----------

  onTapModel(e) {
    const id = e.currentTarget.dataset.id
    const hit = (this.data.models || []).find((m) => m.id === id)
    if (!hit) return

    // 直接把地址带过去，预览页首帧就能拿到，避免异步补 URL 导致场景建不出来
    wx.navigateTo({
      url: `/pages/preview/preview?id=${id}` +
        `&url=${encodeURIComponent(hit.url)}` +
        `&name=${encodeURIComponent(hit.name || '')}` +
        (hit.isLocal ? '&local=1' : '')
    })
  },

  onShareAppMessage() {
    return {
      title: '三维资产库',
      path: '/pages/index/index'
    }
  }
})
