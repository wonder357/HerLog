import { defineComponent, h } from 'vue'

export default defineComponent({
  name: 'H5Form',
  setup(_, { slots }) {
    return () => h('form', slots.default?.())
  }
})

export const H5Label = defineComponent({
  name: 'H5Label',
  setup(_, { slots }) {
    return () => h('label', slots.default?.())
  }
})
