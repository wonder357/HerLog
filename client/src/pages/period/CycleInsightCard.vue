<template>
  <section class="card insight-card" aria-labelledby="cycle-insight-title" :aria-busy="loading">
    <div class="insight-head">
      <h2 id="cycle-insight-title" class="hr-section-title">本周期小结</h2>
      <span v-if="insight?.demo_sample" class="demo-tag">演示内容</span>
      <H5Button class="hr-action refresh" :disabled="loading" @click="load(true)">
        {{ loading ? '生成中…' : '换一批' }}
      </H5Button>
    </div>

    <view v-if="loading && !insight" class="insight-loading" role="status">
      <span class="loading-line wide" />
      <span class="loading-line" />
      <span class="loading-line short" />
    </view>

    <view v-else-if="error && !insight" class="insight-error" role="alert">
      <text class="muted">暂时没能生成小结。</text>
      <H5Button class="hr-action" @click="load(false)">重试</H5Button>
    </view>

    <template v-if="insight">
      <view class="insight-lead">
        <span class="phase-chip">{{ chipLabel }}</span>
        <p class="summary">{{ insight.summary }}</p>
      </view>

      <ul class="groups">
        <li v-for="group in insight.groups" :key="group.key" class="group">
          <span class="group-icon" :class="group.key" aria-hidden="true">
            <HerlogIcon :name="iconFor(group.key)" />
          </span>
          <view class="group-body">
            <h3>{{ group.title }}</h3>
            <ul>
              <li v-for="item in group.items" :key="item">{{ item }}</li>
            </ul>
          </view>
        </li>
      </ul>

      <view v-if="insight.cautions.length" class="cautions">
        <h3>需要留意</h3>
        <ul>
          <li v-for="item in insight.cautions" :key="item">{{ item }}</li>
        </ul>
      </view>

      <p class="insight-foot">
        <span v-if="insight.degraded">模型暂时不可用，先显示规则建议。</span>
        <span v-else-if="error">刷新失败，显示上一次结果。</span>
        <span v-else>更新于 {{ updatedLabel }} ·</span>
        一般建议，不替代医生意见。
      </p>
    </template>
  </section>
</template>

<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import H5Button from '../../components/H5Button'
import HerlogIcon from '../../components/HerlogIcon.vue'
import { getCycleInsight } from '../../services/periodService'
import { ApiRequestError, currentEpoch, StaleSessionError } from '../../services/httpClient'
import type { CycleInsight, InsightGroup } from '../../services/types'

const props = defineProps<{ signature: string }>()
const insight = ref<CycleInsight | null>(null)
const loading = ref(false)
const error = ref(false)
let request = 0

const ICONS: Record<InsightGroup['key'], 'meal' | 'walk' | 'yoga'> = {
  diet: 'meal',
  exercise: 'walk',
  wellbeing: 'yoga'
}

function iconFor(key: InsightGroup['key']) {
  return ICONS[key] ?? 'heart'
}

/** 阶段标签与标题重复时只显示一次，例如「易孕期第 3 天」。 */
const chipLabel = computed(() => {
  const value = insight.value
  if (!value) return ''
  if (!value.headline) return value.phase_label
  return value.headline.includes(value.phase_label) ? value.headline : `${value.headline} · ${value.phase_label}`
})

const updatedLabel = computed(() => {
  const stamp = insight.value?.generated_at
  if (!stamp) return ''
  const moment = new Date(stamp.endsWith('Z') ? stamp : stamp + 'Z')
  if (Number.isNaN(moment.getTime())) return ''
  return `${moment.getMonth() + 1} 月 ${moment.getDate()} 日 ${String(moment.getHours()).padStart(2, '0')}:${String(moment.getMinutes()).padStart(2, '0')}`
})

async function load(refresh: boolean) {
  const id = ++request
  const epoch = currentEpoch()
  loading.value = true
  error.value = false
  try {
    const result = await getCycleInsight(refresh)
    if (id === request && epoch === currentEpoch()) insight.value = result
  } catch (failure) {
    if (id !== request || epoch !== currentEpoch() || failure instanceof StaleSessionError) return
    error.value = true
    if (!insight.value && failure instanceof ApiRequestError && failure.status === 401) return
  } finally {
    if (id === request && epoch === currentEpoch()) loading.value = false
  }
}

watch(() => props.signature, () => void load(false), { immediate: true })
</script>

<style scoped>
.insight-card { padding: 14px 15px 12px; }
.insight-head { display: flex; align-items: center; gap: 8px; }
.insight-head h2 { margin: 0; flex: 1; }
.demo-tag {
  padding: 2px 8px; border-radius: 999px; background: var(--hr-plum-soft);
  color: var(--hr-plum); font-size: 11px; font-weight: 650;
}
.refresh { padding-inline: 0; color: var(--hr-rose-deep); }
.refresh:disabled { opacity: .55; }

.insight-loading { display: grid; gap: 8px; margin-top: 10px; }
.loading-line {
  display: block; height: 12px; border-radius: 6px;
  background: linear-gradient(90deg, var(--hr-paper-deep), var(--hr-rose-soft), var(--hr-paper-deep));
}
.loading-line.wide { width: 92%; }
.loading-line.short { width: 58%; }

.insight-error { display: flex; align-items: center; justify-content: space-between; gap: 8px; margin-top: 8px; }
.insight-lead { margin-top: 8px; }
.phase-chip {
  display: inline-block; padding: 3px 9px; border-radius: 999px;
  background: var(--hr-rose-soft); color: var(--hr-rose-deep); font-size: 12px; font-weight: 650;
}
.summary { margin: 8px 0 0; color: var(--hr-ink); font-size: 14px; line-height: 1.65; }

.groups { display: grid; gap: 10px; margin: 12px 0 0; padding: 0; list-style: none; }
.group {
  display: grid; grid-template-columns: 30px minmax(0, 1fr); gap: 10px;
  padding: 10px 11px; border-radius: 14px; background: var(--hr-paper-deep);
}
.group-icon { display: grid; place-items: center; width: 30px; height: 30px; border-radius: 10px; background: var(--hr-surface); }
.group-icon svg { width: 17px; height: 17px; }
.group-icon.diet { color: var(--hr-peach-ink); }
.group-icon.exercise { color: var(--hr-rose-deep); }
.group-icon.wellbeing { color: var(--hr-plum); }
.group-body h3 { margin: 1px 0 5px; font: 650 13px var(--hr-font); color: var(--hr-ink); }
.group-body ul { display: grid; gap: 4px; margin: 0; padding: 0; list-style: none; }
.group-body li {
  position: relative; padding-left: 10px; color: var(--hr-ink-2); font-size: 13px; line-height: 1.55;
}
.group-body li::before {
  content: ''; position: absolute; left: 0; top: 7px; width: 4px; height: 4px;
  border-radius: 50%; background: var(--hr-line-strong);
}

.cautions { margin-top: 11px; padding: 9px 11px; border-radius: 12px; background: var(--hr-danger-soft); }
.cautions h3 { margin: 0 0 4px; font: 650 12px var(--hr-font); color: var(--hr-danger); }
.cautions ul { margin: 0; padding: 0; list-style: none; display: grid; gap: 3px; }
.cautions li { color: var(--hr-danger); font-size: 12px; line-height: 1.5; }

.insight-foot { margin: 10px 0 0; color: var(--hr-ink-2); font-size: 12px; line-height: 1.5; }
</style>
