import { defineComponent, h, ref } from 'vue'

export default defineComponent({
  name: 'H5Input',
  inheritAttrs: false,
  props: { modelValue: { type: String, required: true } },
  emits: { 'update:modelValue': (value: string) => typeof value === 'string' },
  setup(props, { attrs, emit, expose }) {
    const input = ref<HTMLInputElement | null>(null)
    let composing = false
    function update(event: Event) {
      if (!composing) emit('update:modelValue', (event.target as HTMLInputElement).value)
    }
    expose({ focus: () => input.value?.focus() })
    return () => h('input', {
      ...attrs,
      ref: input,
      value: props.modelValue,
      onInput: update,
      onCompositionstart: () => { composing = true },
      onCompositionend: (event: Event) => {
        composing = false
        update(event)
      }
    })
  }
})
