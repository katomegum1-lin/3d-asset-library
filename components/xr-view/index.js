/**
 * XR-FRAME 渲染组件
 *
 * 本组件的 index.json 里有 "renderer": "xr-frame"，
 * 只有带这个 renderer 的组件里，<xr-scene> 等标签才会被识别。
 *
 * 注意：这类组件不会把自定义事件传递给页面，因此不要依赖 triggerEvent
 * 做页面与组件之间的通信。页面需要的信息请通过 globalData 或重新查询获取。
 */
Component({
  properties: {
    modelUrl: { type: String, value: '' },
    cameraPosition: { type: String, value: '0 1.6 7' },
    // 画布尺寸（CSS 像素），用于让相机宽高比跟屏幕一致，避免画面被拉伸
    width: { type: Number, value: 0 },
    height: { type: Number, value: 0 },
    // 场景清屏色，跟随主题
    clearColor: { type: String, value: '0.06 0.07 0.09 1' }
  },

  methods: {
    handleSceneReady() {},
    handleAssetsLoaded() {}
  }
})
