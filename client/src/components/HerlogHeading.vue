<template>
  <header class="hr-page-heading" :class="'hr-heading--' + presentation">
    <H5Button v-if="backTo || backLabel" class="hr-back" @click="back">{{ backLabel ?? '返回' }}</H5Button>
    <div class="hr-heading-copy">
      <div v-if="eyebrow" class="hr-heading-meta">{{ eyebrow }}</div>
      <h1 class="hr-heading-title">{{ title }}</h1>
      <div v-if="description" class="hr-heading-meta after">{{ description }}</div>
    </div>
    <div v-if="$slots.actions" class="hr-heading-actions"><slot name="actions" /></div>
  </header>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import H5Button from './H5Button'

const props = defineProps<{
  title: string
  eyebrow?: string
  description?: string
  backTo?: string
  backLabel?: string
  variant?: 'primary' | 'detail' | 'auth'
}>()
const emit = defineEmits<{ back: [] }>()
const presentation = computed(() => props.variant ?? (props.backTo || props.backLabel ? 'detail' : 'primary'))

function back() {
  if (!props.backTo) {
    emit('back')
  } else if (getCurrentPages().length > 1) {
    uni.navigateBack()
  } else {
    uni.switchTab({ url: props.backTo })
  }
}
</script>
