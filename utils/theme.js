/**
 * 主题配置
 * clear 是 3D 场景的清屏色（xr-camera 的 clear-color，格式 "r g b a"，取值 0~1）
 */
const THEMES = [
  {
    key: 'dark',
    name: '暗夜',
    pageBg: '#0f1216',
    cardBg: '#171c22',
    border: '#232a33',
    text: '#e8ecf1',
    sub: '#7d8794',
    accent: '#4c9aff',
    navBg: '#0f1216',
    navText: 'white',
    clear: '0.06 0.07 0.09 1'
  },
  {
    key: 'light',
    name: '暖白',
    pageBg: '#f5f3ef',
    cardBg: '#ffffff',
    border: '#e6e1d8',
    text: '#1d2126',
    sub: '#6b7280',
    accent: '#c2703c',
    navBg: '#f5f3ef',
    navText: 'black',
    clear: '0.96 0.95 0.93 1'
  },
  {
    key: 'forest',
    name: '森林',
    pageBg: '#0b1512',
    cardBg: '#13201b',
    border: '#1e3129',
    text: '#e3efe9',
    sub: '#7b9288',
    accent: '#4ad295',
    navBg: '#0b1512',
    navText: 'white',
    clear: '0.05 0.09 0.07 1'
  }
]

const STORAGE_KEY = 'themeKey'

function getTheme() {
  const key = wx.getStorageSync(STORAGE_KEY) || 'dark'
  return THEMES.find((t) => t.key === key) || THEMES[0]
}

function setTheme(key) {
  wx.setStorageSync(STORAGE_KEY, key)
  return getTheme()
}

/** 生成可直接绑到 wxml style 的 CSS 变量串 */
function toStyleVars(theme) {
  return [
    `--page-bg:${theme.pageBg}`,
    `--card-bg:${theme.cardBg}`,
    `--border:${theme.border}`,
    `--text:${theme.text}`,
    `--sub:${theme.sub}`,
    `--accent:${theme.accent}`
  ].join(';')
}

/** 同步导航栏颜色 */
function applyNavBar(theme) {
  wx.setNavigationBarColor({
    frontColor: theme.navText === 'black' ? '#000000' : '#ffffff',
    backgroundColor: theme.navBg,
    fail() {}
  })
}

module.exports = { THEMES, getTheme, setTheme, toStyleVars, applyNavBar }
