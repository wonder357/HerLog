<template>
  <view class="sub-hero">
    <view class="sub-bar">
      <view class="back-btn" @tap="back">
        <view class="back-glyph" />
      </view>
      <view v-if="kicker" class="sub-kicker">{{ kicker }}</view>
    </view>
    <view class="h-title">{{ title }}</view>
    <view v-if="sub" class="h-sub">{{ sub }}</view>
    <slot />
  </view>
</template>

<script setup lang="ts">
const props = withDefaults(
  defineProps<{
    title: string
    kicker?: string
    sub?: string
    fallback?: string
  }>(),
  { kicker: '', sub: '', fallback: '' }
)

function back() {
  uni.navigateBack({
    delta: 1,
    fail: () => {
      if (props.fallback) {
        uni.reLaunch({ url: props.fallback })
      }
    }
  })
}
</script>
