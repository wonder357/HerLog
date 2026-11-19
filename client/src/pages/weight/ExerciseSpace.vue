<template>
  <div class="movement">
    <section class="movement-hero" aria-labelledby="movement-title">
      <img class="hero-image" src="/static/exercise-walk.webp" alt="" width="900" height="600" />
      <div class="hero-copy">
        <time :datetime="today">{{ formatDayLabel(today) }}</time>
        <h2 id="movement-title">今日活动</h2>
        <div v-if="recommended" class="hero-guidance">
          <strong>{{ recommended.title }}</strong>
          <p>{{ recommended.instructions }}</p>
        </div>
        <p v-else class="hero-guidance" :role="cardsLoading ? 'status' : undefined">
          {{ cardsLoading ? '正在读取活动参考…' : '可以先记下今天的运动或休息。' }}
        </p>
      </div>
      <div class="hero-actions">
        <H5Button class="primary" @click="begin(recommended?.activity_code ?? 'walk')">记录活动</H5Button>
        <H5Button class="ghost" @click="begin('rest')">记休息</H5Button>
      </div>
    </section>

    <section class="card activity-week" aria-labelledby="movement-week">
      <div class="section-head">
        <h2 id="movement-week" class="hr-section-title">近 7 天回顾</h2>
        <span v-if="week && !weekLoading && !weekError" class="quiet">{{ weekRange }}</span>
      </div>
      <p v-if="weekLoading" class="quiet state" role="status">正在汇总运动记录…</p>
      <div v-else-if="weekError" class="inline-error" role="alert">
        <span>回顾暂时无法读取。</span><H5Button class="hr-action" @click="loadWeek">重试</H5Button>
      </div>
      <template v-else-if="week">
        <dl class="week-metrics">
          <div><dt>运动次数</dt><dd>{{ week.activity_count }} <small>次</small></dd></div>
          <div><dt>已记时长</dt><dd>{{ week.recorded_minutes }} <small>分钟</small></dd></div>
          <div><dt>休息天数</dt><dd>{{ week.rest_days }} <small>天</small></dd></div>
        </dl>
        <ul class="week-grid" aria-label="每天的运动与休息记录">
          <li v-for="day in week.days" :key="day.day" :aria-label="weekDayLabel(day)"
            :class="{ 'logged-move': day.activities, 'logged-rest': day.rests, today: day.day === today }">
            <span aria-hidden="true">{{ Number(day.day.slice(-2)) }}</span>
            <span class="week-marks" aria-hidden="true">
              <i v-if="day.activities" class="move-mark" /><i v-if="day.rests" class="rest-mark" />
            </span>
          </li>
        </ul>
        <div class="week-legend"><span>● 运动</span><span>◇ 休息</span><span v-if="!week.activity_count && !week.rest_days">这 7 天还没有记录</span></div>
      </template>
    </section>

    <section class="activity-library" aria-labelledby="movement-library">
      <div class="section-head">
        <h2 id="movement-library" class="hr-section-title">活动库</h2>
        <H5Button role="switch" :aria-checked="includeCycle" class="cycle-switch" @click="includeCycle = !includeCycle">
          <i aria-hidden="true" />结合周期
        </H5Button>
      </div>
      <p v-if="includeCycle" class="quiet phase-note">{{ phaseLabel }}</p>
      <div class="filters category-filters" role="group" aria-label="活动分类">
        <H5Button v-for="item in categories" :key="item.code" class="filter-chip" :aria-pressed="category === item.code"
          @click="selectCategory(item.code)">{{ item.label }}</H5Button>
      </div>
      <p v-if="cardsLoading" class="quiet state" role="status">正在读取活动…</p>
      <div v-else-if="cardsError" class="inline-error" role="alert">
        <span>活动暂时无法读取。</span><H5Button class="hr-action" @click="loadCards">重试</H5Button>
      </div>
      <div v-else class="activity-grid">
        <H5Button v-for="item in shownCards" :key="item.activity_code" class="activity-card" :class="item.category"
          :aria-label="'记录' + item.title" @click="begin(item.activity_code)">
          <span class="activity-symbol"><HerlogIcon :name="item.activity_code" /></span>
          <strong>{{ item.title }}</strong>
          <span class="card-instruction">{{ item.instructions }}</span>
          <span class="card-arrow" aria-hidden="true">›</span>
        </H5Button>
      </div>
      <H5Button v-if="!cardsLoading && !cardsError && filteredCards.length > 4" class="hr-action show-more"
        :aria-expanded="expanded" @click="expanded = !expanded">
        {{ expanded ? '收起活动' : '查看全部 ' + filteredCards.length + ' 项活动' }}
      </H5Button>
    </section>

    <section class="card activity-history" aria-labelledby="movement-history">
      <div class="section-head">
        <h2 id="movement-history" class="hr-section-title">运动记录</h2>
        <span v-if="!historyLoading || entries.length" class="quiet">{{ total }} 笔</span>
      </div>
      <div class="history-controls">
        <div class="filters" role="group" aria-label="记录日期范围">
          <H5Button v-for="item in windows" :key="item.code" class="filter-chip" :aria-pressed="historyWindow === item.code"
            @click="historyWindow = item.code">{{ item.label }}</H5Button>
        </div>
        <select v-model="historyActivity" class="history-activity" aria-label="按活动类型筛选记录">
          <option value="">全部类型</option>
          <option v-for="(name, code) in activities" :key="code" :value="code">{{ name }}</option>
        </select>
      </div>
      <div v-if="historyError" class="inline-error" role="alert">
        <span>运动记录没有加载成功。</span><H5Button class="hr-action" @click="loadHistory(failedPage)">重试</H5Button>
      </div>
      <p v-if="historyLoading && !entries.length" class="quiet state" role="status">正在读取运动记录…</p>
      <div v-else-if="!entries.length && !historyError" class="history-empty">
        <HerlogIcon name="period" />
        <span>{{ historyActivity || historyWindow !== 'all' ? '这个范围内暂无记录' : '还没有运动记录' }}</span>
        <H5Button class="hr-action" @click="begin(historyActivity || recommended?.activity_code || 'walk')">记一次活动</H5Button>
      </div>
      <ul v-if="entries.length" class="history-list">
        <li v-for="entry in entries" :key="entry.id">
          <H5Button class="history-row" @click="begin(entry.activity_code, entry)">
            <span class="activity-symbol"><HerlogIcon :name="entry.activity_code" /></span>
            <span class="history-copy">
              <strong>{{ activities[entry.activity_code] }}</strong>
              <span class="quiet">{{ formatMoment(entry.started_at) }}<template v-if="entry.duration_minutes"> · {{ entry.duration_minutes }} 分钟</template></span>
              <span v-if="entry.effort || entry.feeling_code || entry.has_photo" class="history-tags">
                <span v-if="entry.effort">{{ effortNames[entry.effort] }}</span>
                <span v-if="entry.feeling_code">{{ exerciseFeelings[entry.feeling_code] }}</span>
                <span v-if="entry.has_photo">有照片</span>
              </span>
            </span>
            <span class="history-arrow" aria-hidden="true">›</span>
          </H5Button>
        </li>
      </ul>
      <H5Button v-if="nextPage && !historyError" class="hr-action show-more" :disabled="historyLoading" @click="loadHistory(nextPage)">
        {{ historyLoading ? '正在读取…' : '加载更早记录' }}
      </H5Button>
    </section>

    <ExerciseCheckinForm v-if="form" :preset="form.preset" :entry="form.entry" :deleting="deleting" :delete-error="deleteError"
      @close="form = null" @saved="afterSave" @share="share" @remove="remove" />
  </div>
</template>

<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import H5Button from '../../components/H5Button'
import HerlogIcon from '../../components/HerlogIcon.vue'
import ExerciseCheckinForm from './ExerciseCheckinForm.vue'
import { formatDayLabel, formatMoment, todayString } from '../../shared/dates'
import { ApiRequestError, currentEpoch } from '../../services/httpClient'
import { activities, deleteCheckin, effortNames, exerciseCards, exerciseFeelings, exerciseJournal,
  exerciseWeek, phaseNames } from '../../services/wellnessService'
import type { Activity, Checkin, CycleDay, ExerciseCard, ExerciseCategory, ExerciseWeek, ExerciseWindow,
  ShareReference } from '../../services/wellnessService'

const emit = defineEmits<{ share: [ShareReference] }>()
const today = todayString()
const categories = [
  { code: '', label: '全部' }, { code: 'gentle', label: '舒缓' }, { code: 'cardio', label: '有氧' },
  { code: 'strength', label: '力量' }, { code: 'rest', label: '休息' }
] as const
const windows = [{ code: '7', label: '近 7 天' }, { code: '30', label: '近 30 天' }, { code: 'all', label: '全部' }] as const
const form = ref<{ preset: Activity; entry: Checkin | null } | null>(null)
const deleting = ref(false)
const deleteError = ref('')
const week = ref<ExerciseWeek | null>(null)
const weekLoading = ref(true)
const weekError = ref(false)
const includeCycle = ref(true)
const cards = ref<ExerciseCard[]>([])
const phase = ref<CycleDay | null>(null)
const cardsLoading = ref(true)
const cardsError = ref(false)
const category = ref<ExerciseCategory | ''>('')
const expanded = ref(false)
const historyWindow = ref<ExerciseWindow>('30')
const historyActivity = ref<Activity | ''>('')
const entries = ref<Checkin[]>([])
const total = ref(0)
const nextPage = ref<number | null>(null)
const failedPage = ref(1)
const historyLoading = ref(true)
const historyError = ref(false)
let active = true
let weekRequest = 0
let cardsRequest = 0
let historyRequest = 0
const epoch = currentEpoch()
const isActive = () => active && epoch === currentEpoch()

const recommended = computed(() => cardsLoading.value || cardsError.value ? undefined : cards.value[0])
const phaseLabel = computed(() => {
  const context = phase.value
  if (cardsLoading.value) return '正在读取周期参考…'
  if (!context || context.basis === 'unknown') return '按当下感受选择活动。'
  const label = context.phase === 'ovulatory' ? '排卵相关阶段' : phaseNames[context.phase]
  return (context.basis === 'recorded' ? '已记录 · ' : '周期估算 · ') + label + '。活动强度按感受选择。'
})
const filteredCards = computed(() => cards.value.filter(item => !category.value || item.category === category.value))
const shownCards = computed(() => expanded.value ? filteredCards.value : filteredCards.value.slice(0, 4))
const weekRange = computed(() => week.value?.days.length
  ? formatDayLabel(week.value.days[0].day) + ' – ' + formatDayLabel(week.value.days.at(-1)!.day) : '')

function weekDayLabel(day: ExerciseWeek['days'][number]) {
  const status = [day.activities ? '运动 ' + day.activities + ' 次' : '', day.rests ? '已记休息' : ''].filter(Boolean)
  return formatDayLabel(day.day) + '，' + (status.join('，') || '暂无记录')
}

async function loadWeek() {
  const request = ++weekRequest
  const current = () => isActive() && request === weekRequest
  weekLoading.value = true
  weekError.value = false
  try {
    const result = await exerciseWeek()
    if (current()) week.value = result
  } catch {
    if (current()) weekError.value = true
  } finally {
    if (current()) weekLoading.value = false
  }
}

async function loadCards() {
  const request = ++cardsRequest
  const current = () => isActive() && request === cardsRequest
  cardsLoading.value = true
  cardsError.value = false
  phase.value = null
  try {
    const result = await exerciseCards(includeCycle.value)
    if (current()) {
      cards.value = result.cards
      phase.value = result.phase
    }
  } catch {
    if (current()) cardsError.value = true
  } finally {
    if (current()) cardsLoading.value = false
  }
}

async function loadHistory(page = 1) {
  const request = ++historyRequest
  const current = () => isActive() && request === historyRequest
  historyLoading.value = true
  historyError.value = false
  if (page === 1) {
    entries.value = []
    nextPage.value = null
    total.value = 0
  }
  try {
    const result = await exerciseJournal(historyWindow.value, historyActivity.value, page)
    if (current()) {
      const loadedIds = new Set(entries.value.map(item => item.id))
      entries.value = [...entries.value, ...result.items.filter(item => !loadedIds.has(item.id))]
      total.value = result.total
      nextPage.value = result.next_page
    }
  } catch {
    if (current()) {
      failedPage.value = page
      historyError.value = true
    }
  } finally {
    if (current()) historyLoading.value = false
  }
}

function selectCategory(value: ExerciseCategory | '') {
  category.value = value
  expanded.value = false
}

function begin(preset: Activity, entry: Checkin | null = null) {
  deleteError.value = ''
  form.value = { preset, entry }
}

function refreshRecords() {
  void loadHistory()
  void loadWeek()
}

function afterSave(entry: Checkin) {
  if (!isActive()) return
  form.value = null
  refreshRecords()
  uni.showToast({ title: entry.activity_code === 'rest' ? '休息已保存' : '活动已保存', icon: 'none' })
}

function share(entry: Checkin) {
  emit('share', { checkin_id: entry.id, activity: activities[entry.activity_code] })
}

function remove(entry: Checkin) {
  if (deleting.value) return
  deleteError.value = ''
  uni.showModal({
    title: '删除这条运动记录？',
    content: entry.has_photo ? '照片将一并删除，关联的讨论会撤回。' : '关联的讨论会一并撤回。',
    confirmText: '删除',
    success: async result => {
      if (!result.confirm || !isActive()) return
      deleting.value = true
      try {
        await deleteCheckin(entry.id)
        if (!isActive()) return
        form.value = null
        refreshRecords()
        uni.showToast({ title: '记录已删除', icon: 'none' })
      } catch (failure) {
        if (isActive()) deleteError.value = failure instanceof ApiRequestError ? failure.message : '删除未完成，请重试。'
      } finally {
        deleting.value = false
      }
    }
  })
}

watch(includeCycle, loadCards)
watch([historyWindow, historyActivity], () => void loadHistory())
onMounted(() => { void loadCards(); refreshRecords() })
onBeforeUnmount(() => { active = false })
</script>

<style scoped>
.movement { display: grid; gap: 16px; color: var(--hr-ink); min-width: 0; }
.movement .card { margin: 0; }
.movement-hero { position: relative; isolation: isolate; overflow: hidden; border: 1px solid var(--hr-line-strong);
  border-radius: var(--hr-radius-lg); background: var(--hr-peach); padding: 16px; min-height: 174px; display: grid; gap: 12px; align-content: space-between; }
.hero-image { position: absolute; inset: 0; z-index: -2; width: 100%; height: 100%; object-fit: cover; object-position: 68% 48%; }
.movement-hero::before { content: ''; position: absolute; inset: 0; z-index: -1;
  background: linear-gradient(90deg,var(--hr-peach) 8%,color-mix(in srgb,var(--hr-peach) 94%,transparent) 49%,transparent 84%); }
.hero-copy { width: min(65%, 310px); }
.hero-copy time { font-size: 12px; color: var(--hr-peach-ink); font-weight: 680; }
.hero-copy h2 { margin: 2px 0 7px; font: 700 clamp(25px,7vw,38px)/1.25 var(--hr-font); text-wrap: balance; }
.hero-guidance { margin: 0; color: var(--hr-ink); font-size: 13px; line-height: 1.55; }
.hero-guidance strong { display: block; color: var(--hr-rose-deep); font-size: 15px; }
.hero-guidance p { margin: 2px 0 0; }
.hero-actions { display: flex; flex-wrap: wrap; gap: 7px; }
.hero-actions .primary,.hero-actions .ghost { width: auto; min-height: 44px; padding: 7px 15px; font-size: 13px; }
.section-head { display: flex; align-items: center; justify-content: space-between; flex-wrap: wrap; gap: 4px 8px; }
.section-head h2 { margin: 0; }
.quiet { color: var(--hr-ink-2); font-size: 12px; line-height: 1.55; }
.state { margin: 9px 0; }
.activity-week,.activity-history { padding: 14px; }
.week-metrics { display: grid; grid-template-columns: repeat(3,minmax(0,1fr)); margin: 9px 0; gap: 6px; }
.week-metrics div { display: flex; flex-direction: column-reverse; gap: 2px; padding: 7px 3px;
  text-align: center; border-radius: 12px; background: var(--hr-paper); }
.week-metrics dt { font-size: 12px; color: var(--hr-ink-2); }
.week-metrics dd { margin: 0; color: var(--hr-rose-deep); font: 680 clamp(19px,5.7vw,25px)/1.25 var(--hr-font); font-variant-numeric: tabular-nums; }
.week-metrics small { font: 12px var(--hr-font); color: var(--hr-ink-2); }
.week-grid { display: grid; grid-template-columns: repeat(7,minmax(0,1fr)); gap: 4px; list-style: none; padding: 0; margin: 0; }
.week-grid li { display: grid; justify-items: center; align-content: center; min-height: 32px; border-radius: 9px; color: var(--hr-ink-2); background: var(--hr-paper-deep); font-size: 12px; }
.week-grid .today { box-shadow: inset 0 0 0 1px var(--hr-line-strong); font-weight: 650; }
.week-grid .logged-move { background: var(--hr-rose-soft); color: var(--hr-rose-deep); }
.week-grid .logged-rest:not(.logged-move) { background: var(--hr-plum-soft); color: var(--hr-plum); }
.week-marks { display: flex; gap: 3px; align-items: center; height: 6px; }
.week-marks i { box-sizing: border-box; width: 5px; height: 5px; }
.move-mark { border-radius: 50%; background: var(--hr-rose-deep); }
.rest-mark { border: 1px solid var(--hr-plum); transform: rotate(45deg); }
.week-legend { display: flex; flex-wrap: wrap; gap: 4px 10px; margin-top: 6px; color: var(--hr-ink-2); font-size: 12px; }
.week-legend span:first-child { color: var(--hr-rose-deep); }
.week-legend span:nth-child(2) { color: var(--hr-plum); }
.phase-note { margin: 1px 0 7px; }
.cycle-switch { display: inline-flex; align-items: center; gap: 6px; min-height: 44px; padding: 3px 0 3px 6px;
  border: 0; background: transparent; color: var(--hr-ink-2); font: 13px var(--hr-font); }
.cycle-switch i { display: block; position: relative; width: 30px; height: 17px; border-radius: 999px; background: var(--hr-line-strong); }
.cycle-switch i::after { content: ''; position: absolute; left: 2px; top: 2px; width: 13px; height: 13px; border-radius: 50%; background: var(--hr-surface); }
.cycle-switch[aria-checked='true'] i { background: var(--hr-plum); }
.cycle-switch[aria-checked='true'] i::after { left: 15px; }
.filters { display: flex; flex-wrap: wrap; gap: 5px; }
.category-filters { margin-bottom: 8px; }
.filter-chip,.history-activity { min-height: 44px; padding: 5px 9px; border: 1px solid var(--hr-line-strong);
  border-radius: 999px; background: var(--hr-surface); color: var(--hr-ink-2); font: 13px var(--hr-font); }
.filter-chip[aria-pressed='true'] { border-color: var(--hr-rose); color: var(--hr-rose-deep); background: var(--hr-rose-soft); font-weight: 650; }
.activity-grid { display: grid; grid-template-columns: repeat(2,minmax(0,1fr)); gap: 8px; }
.activity-card { position: relative; display: grid; justify-items: start; align-content: start; gap: 5px; padding: 11px;
  min-width: 0; border: 1px solid var(--hr-line); border-radius: 16px; background: var(--hr-surface);
  text-align: left; font: 14px var(--hr-font); color: var(--hr-ink); }
.activity-card strong { font-size: 15px; }
.card-instruction { font-size: 12px; line-height: 1.55; color: var(--hr-ink-2); overflow-wrap: anywhere; }
.card-arrow { position: absolute; top: 9px; right: 11px; color: var(--hr-ink-2); font-size: 21px; }
.activity-symbol { flex: 0 0 36px; width: 36px; height: 36px; display: grid; place-items: center;
  border-radius: 11px; color: var(--hr-rose-deep); background: var(--hr-rose-soft); }
.activity-symbol svg { width: 21px; height: 21px; }
.activity-card.cardio .activity-symbol { color: var(--hr-peach-ink); background: var(--hr-peach); }
.activity-card.strength .activity-symbol { color: var(--hr-taupe); background: var(--hr-taupe-soft); }
.activity-card.rest .activity-symbol { color: var(--hr-plum); background: var(--hr-plum-soft); }
.show-more { margin: 2px auto 0; display: flex; }
.history-controls { display: flex; flex-wrap: wrap; align-items: center; justify-content: space-between; gap: 5px; margin: 9px 0 4px; }
.history-activity { max-width: 100%; }
.history-list { list-style: none; padding: 0; margin: 0; }
.history-list li { border-top: 1px solid var(--hr-line); }
.history-row { display: flex; width: 100%; min-height: 54px; gap: 8px; padding: 8px 1px; align-items: center;
  border: 0; background: transparent; color: var(--hr-ink); text-align: left; }
.history-copy { flex: 1; min-width: 0; display: grid; gap: 2px; }
.history-copy strong { font-size: 15px; }
.history-tags { display: flex; flex-wrap: wrap; gap: 5px; margin-top: 2px; }
.history-tags span { color: var(--hr-ink-2); background: var(--hr-paper-deep); border-radius: 7px; padding: 2px 6px; font-size: 12px; }
.history-arrow { color: var(--hr-rose-deep); font-size: 21px; }
.history-empty { display: grid; justify-items: center; gap: 4px; padding: 16px 4px 0; color: var(--hr-ink-2); font-size: 13px; }
.history-empty svg { width: 24px; height: 24px; color: var(--hr-rose-deep); }
.inline-error { display: flex; align-items: center; justify-content: space-between; gap: 6px; padding: 3px 8px;
  border-radius: 9px; color: var(--hr-danger); background: var(--hr-danger-soft); font-size: 13px; }
</style>
