<template>
  <view>
    <view class="skin-subtitle">{{ observation.site }}</view>
    <view class="skin-date history-time">{{ skinMoment(observation.captured_at) }}</view>
    <view v-if="observation.quality?.level === 'limited'" class="skin-alert" role="status">
      {{ observation.quality.message }}
    </view>
    <PrivateSkinImage v-if="observation.has_image" :id="observation.id" :label="observation.site + '的观察照片'" />
    <view class="history-copy">
      <ObservationCopy :observation="observation" />
    </view>
  </view>
</template>

<script setup lang="ts">
import type { SkinObservation } from '../../services/types'
import { skinMoment } from '../../shared/skin'
import ObservationCopy from './ObservationCopy.vue'
import PrivateSkinImage from './PrivateSkinImage.vue'

defineProps<{ observation: SkinObservation }>()
</script>

<style scoped>
.history-time { margin-bottom: 8px; font-size: 13px; }
.history-copy { margin-top: 8px; overflow-wrap: anywhere; }
</style>
