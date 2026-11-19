<template>
  <view class="dialog-layer">
    <view class="dialog-scrim" aria-hidden="true" @click="close" />
    <section ref="panel" class="dialog-panel" role="dialog" aria-modal="true" :aria-label="title"
      tabindex="-1" @keydown="handleKeys">
      <header class="dialog-header">
        <view class="dialog-grip" aria-hidden="true" />
        <view class="dialog-heading">
          <view>
            <h2 class="dialog-title">{{ title }}</h2>
            <view v-if="context" class="dialog-context">{{ context }}</view>
          </view>
          <H5Button class="dialog-close" :disabled="busy" aria-label="关闭" @click="close">
            <HerlogIcon name="close" />
          </H5Button>
        </view>
      </header>
      <view class="dialog-content"><slot /></view>
      <footer v-if="$slots.actions" class="dialog-actions"><slot name="actions" /></footer>
    </section>
  </view>
</template>

<script setup lang="ts">
import { nextTick, onBeforeUnmount, onMounted, ref } from 'vue'
import H5Button from './H5Button'
import HerlogIcon from './HerlogIcon.vue'

const props = defineProps<{ title: string; context?: string; busy?: boolean }>()
const emit = defineEmits<{ close: [] }>()
const panel = ref<HTMLElement | null>(null)
let opener: HTMLElement | null = null

function close() {
  if (!props.busy) emit('close')
}

onMounted(async () => {
  if (typeof document === 'undefined') return
  opener = document.activeElement instanceof HTMLElement ? document.activeElement : null
  await nextTick()
  panel.value?.focus({ preventScroll: true })
})
onBeforeUnmount(() => {
  if (opener?.isConnected) opener.focus({ preventScroll: true })
})

function handleKeys(event: KeyboardEvent) {
  if (event.key === 'Escape') {
    event.preventDefault()
    event.stopPropagation()
    close()
    return
  }
  if (event.key !== 'Tab' || !panel.value) return
  const controls = [...panel.value.querySelectorAll<HTMLElement>(
    'button:not([disabled]), input:not([disabled]), textarea:not([disabled]), select:not([disabled]), a[href], [tabindex="0"]'
  )].filter(element => element.tabIndex >= 0 && element.getClientRects().length)
  const first = controls[0]
  const last = controls.at(-1)
  if (!first || !last) {
    event.preventDefault()
    return
  }
  if (event.shiftKey && (document.activeElement === first || document.activeElement === panel.value)) {
    event.preventDefault()
    last.focus()
  } else if (!event.shiftKey && document.activeElement === last) {
    event.preventDefault()
    first.focus()
  }
}
</script>

<style scoped>
.dialog-layer { position: fixed; inset: 0; z-index: 35; }
.dialog-scrim { position: absolute; inset: 0; background: #39263183; }
.dialog-panel {
  position: absolute;
  bottom: 0;
  left: 50%;
  display: flex;
  flex-direction: column;
  transform: translateX(-50%);
  box-sizing: border-box;
  width: min(100%, var(--hr-shell-width));
  max-height: 89vh;
  max-height: 89dvh;
  min-height: 0;
  border: 1px solid var(--hr-line);
  border-radius: var(--hr-radius-lg) var(--hr-radius-lg) 0 0;
  background: var(--hr-surface);
  color: var(--hr-ink);
  box-shadow: 0 -14px 48px -24px #5e314b6c;
}
.dialog-panel:focus { outline: none; }
.dialog-header { padding: 9px 16px 12px; }
.dialog-grip { width: 36px; height: 4px; margin: 0 auto 8px; border-radius: 9px; background: var(--hr-line-strong); }
.dialog-heading { display: flex; justify-content: space-between; align-items: center; gap: 10px; }
.dialog-title { font: 690 21px/1.25 var(--hr-font); margin: 0; }
.dialog-context { margin-top: 4px; color: var(--hr-ink-2); font-size: 13px; }
.dialog-close {
  flex: 0 0 44px;
  display: grid;
  place-items: center;
  min-height: 44px;
  padding: 0;
  border: 0;
  border-radius: 50%;
  background: var(--hr-paper-deep);
  color: var(--hr-rose-deep);
}
.dialog-close svg { width: 18px; height: 18px; }
.dialog-content {
  min-height: 0;
  overflow-y: auto;
  overscroll-behavior: contain;
  padding: 1px 16px 12px;
  scroll-padding: 6px 0 14px;
}
.dialog-content:last-child { padding-bottom: calc(16px + env(safe-area-inset-bottom)); }
.dialog-actions {
  display: flex;
  gap: 8px;
  align-items: center;
  padding: 10px 16px calc(12px + env(safe-area-inset-bottom));
  border-top: 1px solid var(--hr-line);
  background: var(--hr-surface);
}
</style>
