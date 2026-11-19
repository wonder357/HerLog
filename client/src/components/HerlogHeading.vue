<template>
  <H5Button v-if="backTo" class="hr-back" @click="back">{{ backLabel ?? '返回' }}</H5Button>
  <view class="hr-page-heading">
    <view>
      <view v-if="eyebrow" class="hr-heading-meta">{{ eyebrow }}</view>
      <h1 class="hr-heading-title">{{ title }}</h1>
      <view v-if="description" class="hr-heading-meta after">{{ description }}</view>
    </view>
    <view v-if="$slots.actions" class="hr-heading-actions"><slot name="actions" /></view>
  </view>
</template>

<script setup lang="ts">
import H5Button from './H5Button'

const props = defineProps<{ title: string; eyebrow?: string; description?: string; backTo?: string; backLabel?: string }>()
function back() {
  if (getCurrentPages().length > 1) {
    uni.navigateBack()
  } else if (props.backTo) {
    uni.switchTab({ url: props.backTo })
  }
}
</script>
