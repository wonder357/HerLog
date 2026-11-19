<template>
  <view class="studio">
    <HerlogHeading title="皮肤">
      <template #actions><SkinButton class="hr-action" @click="emit('history', false)">照片历史</SkinButton></template>
    </HerlogHeading>
    <view class="studio-tabs" aria-label="皮肤模块">
      <SkinButton v-for="item in tabs" :key="item.key" class="studio-tab"
        :class="{ current: tab === item.key }" :aria-pressed="tab === item.key" @click="switchTab(item.key)">{{ item.label }}</SkinButton>
    </view>

    <template v-if="tab === 'today'">
      <view class="today-hero">
        <view class="hero-copy">
          <view class="date-line">{{ formatDayLabel(today) }}</view>
          <view class="hero-title">今天，皮肤感觉怎样？</view>
          <view class="hero-actions">
            <SkinButton class="studio-primary" @click="openEditor(today)">{{ todayEntry ? '更新今日记录' : '记今日状态' }}</SkinButton>
            <SkinButton class="studio-secondary" @click="emit('capture')">拍照观察</SkinButton>
          </view>
        </view>
      </view>

      <view v-if="loadError" class="studio-alert" role="alert">{{ loadError }} <SkinButton class="studio-text" @click="loadToday">重试</SkinButton></view>
      <view class="mini-grid">
        <SkinButton class="mini-panel" @click="openEditor(today, true)">
          <view class="mini-label">肤质自评</view><view class="mini-value">{{ typeTitle(todayEntry?.skin_type ?? latestEntry?.skin_type ?? null) }}</view>
        </SkinButton>
        <SkinButton class="mini-panel" @click="openEditor(today)">
          <view class="mini-label">今日舒适度</view><view class="mini-value">{{ todayEntry?.comfort ? comfortNames[todayEntry.comfort] : '待记录' }}</view>
        </SkinButton>
        <SkinButton class="mini-panel" @click="switchTab('care')">
          <view class="mini-label">日光防护</view><view class="mini-value">{{ sunLogged ? '已记录' : '去看看' }}</view>
        </SkinButton>
      </view>

      <view class="studio-panel featured">
        <view class="featured-main">
          <view class="panel-kicker">护理参考</view>
          <view class="panel-title">{{ suggested.title }}</view>
          <view class="studio-muted">{{ suggested.body }}</view>
          <SkinButton class="studio-text" @click="switchTab('care')">查看护理参考 ↗</SkinButton>
        </view>
        <HerlogIcon name="skin" class="feature-symbol" />
      </view>

      <view class="studio-panel">
        <view class="panel-header">
          <view><view class="panel-kicker">回看</view><view class="panel-title">最近一次照片观察</view></view>
          <SkinButton class="studio-text" @click="emit('history', true)">同部位对比</SkinButton>
        </view>
        <view v-if="latest" class="latest-record">
          <PrivateSkinImage :id="latest.id" :label="latest.site + '的最近照片'" />
          <view class="record-copy">
            <view>{{ latest.site }} · {{ formatMoment(latest.captured_at) }}</view>
            <ObservationCopy :observation="latest" summary />
          </view>
        </view>
        <view v-else-if="photoLoading" class="studio-muted" role="status">正在读取照片观察…</view>
        <view v-else-if="photoError" class="studio-muted" role="alert">照片观察没有加载成功。<SkinButton class="studio-text" @click="emit('refresh-photo')">重试</SkinButton></view>
        <view v-else class="studio-muted">保存一次照片观察后，可以在这里回看。</view>
      </view>
    </template>

    <template v-else-if="tab === 'calendar'">
      <view class="studio-panel">
        <view class="panel-header"><view class="panel-title">记录日历</view><SkinButton class="studio-text" @click="emit('history', true)">照片对比</SkinButton></view>
        <view class="studio-month">
          <SkinButton class="month-nav" aria-label="上个月" @click="moveMonth(-1)">‹</SkinButton>
          <view>{{ formatMonthLabel(month) }}</view>
          <SkinButton class="month-nav" aria-label="下个月" :disabled="month >= startOfMonth(today)" @click="moveMonth(1)">›</SkinButton>
        </view>
        <view class="studio-grid">
          <text v-for="value in weekdays" :key="value" class="weekday">{{ value }}</text>
          <view v-for="number in grid.leading" :key="'blank-' + number" />
          <SkinButton v-for="day in grid.days" :key="day" class="studio-day" :disabled="day > today"
            :aria-pressed="day === dateSelected" :class="{ selected: day === dateSelected }"
            :aria-label="formatDayLabel(day) + (journalDays.has(day) ? '，有日记' : '') + (photoDays.has(day) ? '，有照片' : '')"
            @click="dateSelected = day">
            {{ Number(day.slice(-2)) }}
            <view class="dots"><i v-if="journalDays.has(day)" /><i v-if="photoDays.has(day)" class="photo-dot" /></view>
          </SkinButton>
        </view>
        <view class="studio-muted legend"><i /> 日记 <i class="photo-dot" /> 照片</view>
      </view>
      <view v-if="calendarError" class="studio-alert" role="alert">这个月没有加载成功。<SkinButton class="studio-text" @click="loadMonth">重试</SkinButton></view>
      <view class="studio-panel" :aria-busy="calendarLoading">
        <view class="panel-header"><view class="panel-title">{{ formatDayLabel(dateSelected) }}</view><SkinButton class="studio-text" :disabled="calendarLoading || calendarError" @click="openEditor(dateSelected)">{{ selectedEntry ? '编辑日记' : '补记日记' }}</SkinButton></view>
        <view v-if="selectedEntry" class="comparison-facts">
          <view>肤质自评 <strong>{{ typeTitle(selectedEntry.skin_type) }}</strong></view>
          <view>舒适度 <strong>{{ selectedEntry.comfort ? comfortNames[selectedEntry.comfort] + ' · ' + selectedEntry.comfort + '/5' : '未记录' }}</strong></view>
          <view>感受 <strong>{{ selectedEntry.sensations.map(code => sensationNames[code]).join('、') || '未记录' }}</strong></view>
          <view>护理 <strong>{{ selectedEntry.routine.map(code => routineNames[code]).join('、') || '未记录' }}</strong></view>
          <view v-if="selectedEntry.note" class="studio-muted">{{ selectedEntry.note }}</view>
          <SkinButton class="studio-secondary" @click="chooseDay(selectedEntry)">{{ comparedDays.some(item => item.day === dateSelected) ? '取消选择这天' : '选作日期对比' }}</SkinButton>
        </view>
        <view v-else class="studio-muted">{{ calendarLoading ? '正在读取日历…' : calendarError ? '日期记录暂不可用' : '这天还没有护理日记。' }}</view>
        <SkinButton v-if="photoDays.has(dateSelected)" class="studio-text" @click="emit('history', false, dateSelected)">查看当天照片 ↗</SkinButton>
      </view>
      <view v-if="comparedDays.length" class="studio-panel">
        <view class="panel-header"><view class="panel-title">两天的肤质与状态</view><SkinButton class="studio-text" @click="comparedDays = []">清空</SkinButton></view>
        <view v-if="comparedDays.length === 1" class="studio-muted">已选 {{ formatDayLabel(comparedDays[0].day) }}。可以换月再选一天。</view>
        <view v-else class="journal-compare">
          <view v-for="entry in sortedDays" :key="entry.day" class="journal-compare-side">
            <strong>{{ entry.day.slice(0, 4) }} 年 {{ formatDayLabel(entry.day) }}</strong>
            <view>{{ typeTitle(entry.skin_type) }}</view>
            <view class="studio-muted">{{ entry.comfort ? comfortNames[entry.comfort] + ' · ' + entry.comfort + '/5' : '舒适度未记录' }}</view>
            <view class="studio-muted">{{ entry.sensations.map(code => sensationNames[code]).join('、') || '感受未记录' }}</view>
            <view class="studio-muted">{{ entry.routine.map(code => routineNames[code]).join('、') || '护理未记录' }}</view>
          </view>
        </view>
      </view>
    </template>

    <template v-else-if="tab === 'care'">
      <view class="studio-panel care-head">
        <view class="panel-kicker">按自己的感受选择</view>
        <view class="panel-title">护理与日光防护</view>
        <view class="studio-muted">把有用的护理习惯留在日记里，按日期回看。</view>
      </view>
      <view class="studio-panel featured">
        <view class="featured-main">
          <view class="panel-kicker">{{ typeTitle(latestEntry?.skin_type ?? null) }}</view>
          <view class="panel-title">{{ suggested.title }}</view>
          <view class="studio-muted">{{ suggested.body }}</view>
          <view v-if="stateTip" class="sensation-tip">{{ stateTip }}</view>
          <SkinButton class="studio-text" @click="openEditor(today, true)">去做肤质自评 ↗</SkinButton>
        </view>
        <HerlogIcon name="skin" class="feature-symbol" />
      </view>
      <view class="studio-panel">
        <view class="panel-title">肤色回看与防晒</view>
        <view class="studio-muted">户外可结合阴凉处、防晒衣帽和广谱 SPF 30+ 防晒。用相近光线、角度拍照，方便回看同一部位。</view>
        <view class="studio-control-row">
          <SkinButton class="studio-primary" @click="openEditor(today, false, true)">记防晒</SkinButton>
          <SkinButton class="studio-secondary" @click="emit('history', true)">看同部位照片</SkinButton>
        </view>
        <a class="studio-source" href="https://www.aad.org/public/everyday-care/sun-protection/shade-clothing-sunscreen/how-to-select-sunscreen" target="_blank" rel="noopener noreferrer">护理参考来源 · 美国皮肤科学会</a>
      </view>
    </template>

    <HerlogSheet v-if="editor" title="护理日记" :context="formatDayLabel(editDay)" :busy="saving" @close="closeEditor">
        <view class="field-block">
          <view class="field-title">肤质自评</view>
          <view v-if="questionnaire" class="quiz">
            <view class="studio-muted">回想近一周，哪些部位比较容易泛油光？</view>
            <view class="chips">
              <SkinButton v-for="item in shineOptions" :key="item.code" :class="{ selected: shine === item.code }" @click="shine = item.code">{{ item.label }}</SkinButton>
            </view>
            <view class="studio-muted">洁面后常觉得紧绷吗？</view>
            <view class="chips">
              <SkinButton :class="{ selected: tight === 'often' }" @click="tight = 'often'">经常</SkinButton>
              <SkinButton :class="{ selected: tight === 'rarely' }" @click="tight = 'rarely'">很少</SkinButton>
              <SkinButton class="studio-text" :disabled="!shine || !tight" @click="applyQuiz">使用自评结果</SkinButton>
            </view>
          </view>
          <view v-else class="chips"><SkinButton @click="questionnaire = true">回答两个问题</SkinButton></view>
          <view class="chips">
            <SkinButton v-for="(title, code) in typeNames" :key="code" :class="{ selected: edit.skin_type === code }" @click="edit.skin_type = edit.skin_type === code ? null : code">{{ title }}</SkinButton>
          </view>
        </view>
        <view class="field-block">
          <view class="field-title">今天的舒适度 · 自评</view>
          <view class="studio-muted">按你的真实感受选择，选填。</view>
          <view class="score-row">
            <SkinButton v-for="value in 5" :key="value" :aria-label="comfortNames[value]" :aria-pressed="edit.comfort === value"
              :class="{ selected: edit.comfort === value }" @click="edit.comfort = edit.comfort === value ? null : value">
              <strong>{{ value }}</strong><small>{{ comfortNames[value] }}</small>
            </SkinButton>
          </view>
        </view>
        <view class="field-block">
          <view class="field-title">今天的感受</view>
          <view class="chips">
            <SkinButton v-for="(label, code) in sensationNames" :key="code" :class="{ selected: edit.sensations.includes(code) }" @click="toggleSensation(code)">{{ label }}</SkinButton>
          </view>
        </view>
        <view class="field-block">
          <view class="field-title">做过的护理</view>
          <view class="chips">
            <SkinButton v-for="(label, code) in routineNames" :key="code" :class="{ selected: edit.routine.includes(code) }" @click="toggleRoutine(code)">{{ label }}</SkinButton>
          </view>
          <textarea v-model="editNote" aria-label="仅自己可见的备注" class="journal-note" placeholder="备注 · 仅自己可见" maxlength="400" />
        </view>
        <view v-if="editorError" class="studio-alert" role="alert">{{ editorError }}</view>
        <template #actions>
          <SkinButton v-if="editingExisting" class="studio-text" :disabled="saving" @click="removeEntry">删除</SkinButton>
          <SkinButton class="studio-primary" :disabled="saving" @click="submit">{{ saving ? '保存中…' : '保存日记' }}</SkinButton>
        </template>
    </HerlogSheet>
  </view>
</template>

<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import SkinButton from '../../components/H5Button'
import HerlogHeading from '../../components/HerlogHeading.vue'
import HerlogIcon from '../../components/HerlogIcon.vue'
import HerlogSheet from '../../components/HerlogSheet.vue'
import ObservationCopy from './ObservationCopy.vue'
import PrivateSkinImage from './PrivateSkinImage.vue'
import { formatDayLabel, formatMoment, formatMonthLabel, monthGrid, shiftMonth, startOfMonth, todayString } from '../../shared/dates'
import { groupSkinDays, selfAssessedSkinType, skinMonthRange } from '../../shared/skin'
import { listObservations } from '../../services/skinService'
import { deleteJournal, latestJournal, listJournal, saveJournal } from '../../services/wellnessService'
import { currentEpoch } from '../../services/httpClient'
import type { SkinSummaryItem } from '../../services/types'
import type { JournalDay, JournalInput, SkinRoutine, SkinSensation, SkinType } from '../../services/wellnessService'

defineProps<{ latest: SkinSummaryItem | null; photoLoading: boolean; photoError: boolean }>()
const emit = defineEmits<{ capture: []; history: [compare: boolean, day?: string]; 'refresh-photo': [] }>()
const tabs = [{ key: 'today', label: '今日' }, { key: 'calendar', label: '日历' }, { key: 'care', label: '护理指南' }] as const
type Tab = typeof tabs[number]['key']
const tab = ref<Tab>('today')
const today = todayString()
const month = ref(startOfMonth(today))
const dateSelected = ref(today)
const weekdays = ['一','二','三','四','五','六','日']
const typeNames: Record<SkinType, string> = { dry: '偏干', oily: '偏油', combination: '混合', balanced: '较平衡', unsure: '待观察' }
const sensationNames: Record<SkinSensation, string> = { tight: '紧绷', shine: '有油光', sensitive: '易刺痒', rough: '有粗糙感', redness: '感觉偏红' }
const routineNames: Record<SkinRoutine, string> = { cleanse: '温和清洁', moisturize: '保湿', sunscreen: '涂防晒', shade: '找阴凉', cover: '衣帽遮挡', reapply: '补涂' }
const comfortNames: Record<number, string> = { 1: '不舒服', 2: '略不适', 3: '一般', 4: '较舒适', 5: '很舒适' }
const shineOptions = [{ code: 'all', label: '全脸' }, { code: 't_zone', label: '主要在 T 区' }, { code: 'little', label: '很少泛油光' }] as const
const advice = {
  dry: { title: '留意清洁后的紧绷感', body: '可以尝试温和清洁和保湿，把清洁后的感受记下来。' },
  oily: { title: '从温和清洁开始', body: '按需温和清洁，也可以选清爽的保湿产品。把不同部位的油光分开记录。' },
  combination: { title: '按部位观察', body: '分开记录 T 区和两颊的感受，护理步骤按各部位当下需要选择。' },
  balanced: { title: '保持简单的护理步骤', body: '按需要做温和清洁、保湿和日光防护，换季时留意变化。' },
  unsure: { title: '先用一套简单步骤', body: '按需要选择温和清洁和保湿。留意洁面后紧绷和白天泛油光出现的部位。' }
}
const journalDays = ref(new Map<string, JournalDay>())
const photoDays = ref(new Map<string, SkinSummaryItem[]>())
const todayEntry = ref<JournalDay | null>(null)
const latestEntry = ref<JournalDay | null>(null)
const comparedDays = ref<JournalDay[]>([])
const loadError = ref('')
const calendarLoading = ref(false)
const calendarError = ref(false)
const grid = computed(() => monthGrid(month.value))
const selectedEntry = computed(() => journalDays.value.get(dateSelected.value))
const sortedDays = computed(() => [...comparedDays.value].sort((a,b) => a.day.localeCompare(b.day)))
const sunLogged = computed(() => todayEntry.value?.routine.some(code => ['sunscreen', 'shade', 'cover', 'reapply'].includes(code)))
const suggested = computed(() => advice[todayEntry.value?.skin_type ?? latestEntry.value?.skin_type ?? 'unsure'])
const stateTip = computed(() => {
  const sensations = (todayEntry.value ?? latestEntry.value)?.sensations ?? []
  if (sensations.includes('sensitive') || sensations.includes('redness')) return '近期有刺痒或泛红感时，先回看用过的产品，避免同时加入多种新产品。'
  if (sensations.includes('tight') || sensations.includes('rough')) return '如果感觉紧绷，可以记下清洁时间和保湿后的个人感受。'
  if (sensations.includes('shine')) return '可以分开记录 T 区和两颊的油光。'
  return ''
})
const editor = ref(false)
const editDay = ref(today)
const edit = ref<JournalInput>(blank())
const editNote = ref('')
const editorError = ref('')
const editingExisting = ref(false)
const questionnaire = ref(false)
const shine = ref<typeof shineOptions[number]['code'] | null>(null)
const tight = ref<'often' | 'rarely' | null>(null)
const saving = ref(false)
const ownerEpoch = currentEpoch()
let alive = true
let loadVersion = 0
let todayVersion = 0
const current = () => alive && ownerEpoch === currentEpoch()
onBeforeUnmount(() => { alive = false })
onMounted(loadToday)
function typeTitle(value: SkinType | null) { return value ? typeNames[value] : '待自评' }
function blank(): JournalInput { return { skin_type: null, comfort: null, sensations: [], routine: [], note: null } }

async function loadToday() {
  const version = ++todayVersion
  loadError.value = ''
  try {
    const [entries, latest] = await Promise.all([listJournal(today, today), latestJournal()])
    if (!current() || version !== todayVersion) return
    todayEntry.value = entries[0] ?? null
    latestEntry.value = latest
  } catch {
    if (current() && version === todayVersion) loadError.value = '护理记录没有加载成功'
  }
}
async function loadMonth() {
  const version = ++loadVersion
  calendarLoading.value = true
  calendarError.value = false
  const range = skinMonthRange(month.value)
  try {
    const [entries, photos] = await Promise.all([listJournal(range.from, range.to), listObservations(range)])
    if (!current() || version !== loadVersion) return
    journalDays.value = new Map(entries.map(entry => [entry.day, entry]))
    photoDays.value = groupSkinDays(photos)
  } catch {
    if (current() && version === loadVersion) calendarError.value = true
  } finally {
    if (version === loadVersion) calendarLoading.value = false
  }
}
function switchTab(value: Tab) {
  tab.value = value
  if (value === 'calendar') void loadMonth()
}
function moveMonth(delta: number) {
  month.value = shiftMonth(month.value, delta)
  dateSelected.value = month.value === startOfMonth(today) ? today : month.value
  void loadMonth()
}
function chooseDay(entry: JournalDay) {
  if (comparedDays.value.some(item => item.day === entry.day)) {
    comparedDays.value = comparedDays.value.filter(item => item.day !== entry.day)
  } else if (comparedDays.value.length < 2) {
    comparedDays.value = [...comparedDays.value, entry]
  } else uni.showToast({ title: '请先取消一天，再选新日期', icon: 'none' })
}
function openEditor(day: string, quiz = false, prefillSun = false) {
  if (tab.value === 'calendar' && (calendarLoading.value || calendarError.value)) return
  const entry = day === today ? todayEntry.value ?? journalDays.value.get(day) : journalDays.value.get(day)
  editDay.value = day
  edit.value = entry ? {
    skin_type: entry.skin_type, comfort: entry.comfort, sensations: [...entry.sensations], routine: [...entry.routine], note: entry.note
  } : blank()
  if (prefillSun && !edit.value.routine.includes('sunscreen')) edit.value.routine.push('sunscreen')
  editNote.value = entry?.note ?? ''
  editingExisting.value = Boolean(entry)
  editorError.value = ''
  questionnaire.value = quiz
  shine.value = null
  tight.value = null
  editor.value = true
}
function closeEditor() { if (!saving.value) editor.value = false }
function toggleSensation(code: SkinSensation) {
  edit.value.sensations = edit.value.sensations.includes(code) ? edit.value.sensations.filter(value => value !== code) : [...edit.value.sensations, code]
}
function toggleRoutine(code: SkinRoutine) {
  edit.value.routine = edit.value.routine.includes(code) ? edit.value.routine.filter(value => value !== code) : [...edit.value.routine, code]
}
function applyQuiz() {
  edit.value.skin_type = selfAssessedSkinType(shine.value, tight.value)
  questionnaire.value = false
}
async function submit() {
  if (saving.value) return
  const day = editDay.value
  const payload = { ...edit.value, note: editNote.value.trim() || null }
  if (payload.skin_type === null && payload.comfort === null && !payload.sensations.length && !payload.routine.length && !payload.note) {
    editorError.value = '至少记录一项感受或护理内容'
    return
  }
  saving.value = true
  editorError.value = ''
  try {
    const entry = await saveJournal(day, payload)
    if (!current()) return
    todayVersion += 1
    if (day === today) todayEntry.value = entry
    if (!latestEntry.value || day >= latestEntry.value.day) latestEntry.value = entry
    comparedDays.value = comparedDays.value.map(item => item.day === day ? entry : item)
    editor.value = false
    uni.showToast({ title: '护理日记已保存', icon: 'none' })
    if (tab.value === 'calendar') void loadMonth()
  } catch {
    if (current()) editorError.value = '没有保存成功，可以重试'
  } finally {
    saving.value = false
  }
}
function removeEntry() {
  const day = editDay.value
  uni.showModal({
    title: '删除这天的日记？', content: '相应小组卡片会撤回，已经保存的照片观察可以继续回看。',
    success: async result => {
      if (!result.confirm || !current() || saving.value) return
      saving.value = true
      try {
        await deleteJournal(day)
        if (!current()) return
        comparedDays.value = comparedDays.value.filter(item => item.day !== day)
        editor.value = false
        void loadToday()
        if (tab.value === 'calendar') void loadMonth()
      } catch {
        if (current()) editorError.value = '日记没有删除成功'
      } finally {
        saving.value = false
      }
    }
  })
}
</script>

<style scoped src="./studio.css"></style>
