const { getTheme, toStyleVars, applyNavBar } = require('../../utils/theme')

Page({
  data: {
    avatarUrl: '',
    nickName: '',
    styleVars: ''
  },

  onLoad() {
    const theme = getTheme()
    this.setData({ styleVars: toStyleVars(theme) })
    applyNavBar(theme)

    const saved = wx.getStorageSync('userProfile')
    if (saved) {
      this.setData({ avatarUrl: saved.avatarUrl || '', nickName: saved.nickName || '' })
    }
  },

  onChooseAvatar(e) {
    const temp = e.detail.avatarUrl
    // 临时路径会过期，存一份到本地
    wx.getFileSystemManager().saveFile({
      tempFilePath: temp,
      success: (res) => this.setData({ avatarUrl: res.savedFilePath }),
      fail: () => this.setData({ avatarUrl: temp })
    })
  },

  onNickInput(e) {
    this.setData({ nickName: e.detail.value })
  },

  onSubmit() {
    const nickName = (this.data.nickName || '').trim()
    if (!nickName) {
      wx.showToast({ title: '先填个昵称吧', icon: 'none' })
      return
    }

    wx.setStorageSync('userProfile', {
      avatarUrl: this.data.avatarUrl,
      nickName
    })
    wx.removeStorageSync('loginSkipped')

    wx.reLaunch({ url: '/pages/index/index' })
  },

  onSkip() {
    wx.setStorageSync('loginSkipped', true)
    wx.reLaunch({ url: '/pages/index/index' })
  }
})
