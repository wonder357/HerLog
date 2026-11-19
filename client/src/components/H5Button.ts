import { defineComponent, h } from 'vue'

/** H5 使用原生按钮，让浏览器处理焦点、键盘激活和禁用状态。 */
export default defineComponent({
  name: 'H5Button',
  inheritAttrs: false,
  setup(_, { attrs, slots }) {
    return () => h('button', { type: 'button', ...attrs }, slots.default?.())
  }
})
