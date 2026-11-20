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
        <img class="photo-examples" src="/static/skin-photo-guide.png" alt="拍照示例：正面自然表情与微笑侧倾" />
        <view class="hero-copy">
          <view class="hero-top">
            <view class="date-line">{{ formatDayLabel(today) }}</view>
            <HerlogMascot class="hero-mascot" pose="care" :size="64" alt="" />
          </view>
          <view class="hero-title">今天，皮肤感觉怎样？</view>
          <view class="hero-actions">
            <SkinButton class="primary hero-button" @click="emit('capture')"><HerlogIcon name="camera" />拍照记录</SkinButton>
            <SkinButton class="ghost hero-button" @click="openEditor(today)">{{ todayEntry ? '编辑自评' : '记录感受' }}</SkinButton>
          </view>
        </view>
      </view>

      <view v-if="loadError" class="studio-alert" role="alert">{{ loadError }} <SkinButton class="studio-text" @click="loadToday">重试</SkinButton></view>
      <view class="mini-grid">
        <SkinButton class="mini-panel" @click="openEditor(today)">
          <view class="mini-label">肤质自评</view><view class="mini-value">{{ typeTitle(todayEntry?.skin_type ?? latestEntry?.skin_type ?? null) }}</view>
        </SkinButton>
        <SkinButton class="mini-panel" @click="openEditor(today)">
          <view class="mini-label">今日舒适度</view><view class="mini-value">{{ todayEntry?.comfort ? comfortNames[todayEntry.comfort] : '待记录' }}</view>
        </SkinButton>
        <SkinButton class="mini-panel" @click="switchTab('care')">
          <view class="mini-label">日光防护</view><view class="mini-value">{{ sunLogged ? '已记录' : '去看看' }}</view>
        </SkinButton>
      </view>

      <view class="studio-panel sample-panel">
        <view class="panel-header">
          <view><view class="panel-kicker">拍照示例</view><view class="panel-title">照着这样拍</view></view>
        </view>
        <view class="sample-grid">
          <view v-for="sample in SKIN_SAMPLES" :key="sample.src" class="sample-item">
            <image class="sample-photo" :src="sample.src" mode="aspectFill" :aria-label="sample.alt" />
            <view class="sample-meta"><strong>{{ sample.site }}</strong>{{ sample.note }}</view>
          </view>
        </view>
        <view class="studio-muted">示例为展示用照片。拍照时保持光线均匀、避开滤镜，按部位选择对应的取景范围。</view>
      </view>

      <view class="studio-panel featured care-preview">
        <view class="featured-main">
          <view class="panel-kicker">护理参考</view>
          <h2 class="panel-title">{{ suggested.title }}</h2>
          <p class="care-preview-copy">{{ suggested.body }}</p>
          <SkinButton class="studio-text care-preview-link" @click="switchTab('care')">查看指南详情 ›</SkinButton>
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
            <view class="record-meta"><strong>{{ latest.site }}</strong><text>{{ formatMoment(latest.captured_at) }}</text></view>
            <ObservationCopy :observation="latest" summary />
          </view>
        </view>
        <view v-else-if="photoLoading" class="studio-muted" role="status">正在读取照片观察…</view>
        <view v-else-if="photoError" class="studio-muted" role="alert">照片观察没有加载成功。<SkinButton class="studio-text" @click="emit('refresh-photo')">重试</SkinButton></view>
        <view v-else class="studio-muted">
          <text>保存一次照片观察后，可以在这里回看。</text>
        </view>
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
        <view v-for="photo in selectedPhotos" :key="photo.id" class="day-photo">
          <PrivateSkinImage :id="photo.id" :label="photo.site + '的照片'" />
          <view><strong>{{ photo.site }} · {{ formatMoment(photo.captured_at) }}</strong><ObservationCopy :observation="photo" summary /></view>
        </view>
        <view v-if="!calendarLoading && !calendarError && !selectedPhotos.length" class="studio-muted">这天没有照片观察。</view>
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
      <view class="studio-panel featured">
        <view class="featured-main">
          <view class="panel-kicker">{{ typeTitle(latestEntry?.skin_type ?? null) }}</view>
          <view class="panel-title">{{ suggested.title }}</view>
          <view class="studio-muted">{{ suggested.body }}</view>
          <view v-if="stateTip" class="sensation-tip">{{ stateTip }}</view>
          <SkinButton class="studio-text" @click="openEditor(today)">去做肤质自评 ↗</SkinButton>
        </view>
        <HerlogIcon name="skin" class="feature-symbol" />
      </view>
      <view class="studio-panel">
        <h2 class="panel-title">日常三步</h2>
        <ol class="guide-steps">
          <li><strong>清洁：</strong>温和清洗，不用力搓。</li>
          <li><strong>保湿：</strong>干燥时选更滋润的面霜；偏油时选清爽乳液。</li>
          <li><strong>防晒：</strong>外出用广谱 SPF 30+ 防晒，搭配帽子和遮阴。</li>
        </ol>
        <SkinButton class="studio-secondary" @click="guideDetail = 1">查看护理方法详情 ›</SkinButton>
        <view class="studio-control-row">
          <SkinButton class="studio-primary" @click="openEditor(today, true)">记防晒</SkinButton>
          <SkinButton class="studio-secondary" @click="emit('history', true)">看同部位照片</SkinButton>
        </view>
      </view>
      <section class="studio-panel guide-reference">
        <h2 class="panel-title" id="guide-skin-types">肤质对照</h2>
        <table class="guide-table" aria-labelledby="guide-skin-types">
          <thead><tr><th scope="col">肤质</th><th scope="col">常见感受</th><th scope="col">护理重点</th></tr></thead>
          <tbody>
            <tr><th scope="row">中性</th><td>不太油，也不紧绷</td><td>维持基础保湿</td></tr>
            <tr><th scope="row">干性</th><td>容易紧绷、起屑</td><td>温和清洁，加强保湿</td></tr>
            <tr><th scope="row">油性</th><td>容易泛油光</td><td>用清爽保湿，别过度清洁</td></tr>
          </tbody>
        </table>
        <SkinButton class="studio-secondary" @click="guideDetail = 0">查看肤质分类详情 ›</SkinButton>
      </section>
      <section class="studio-panel guide-reference">
        <h2 class="panel-title">遇到这些情况</h2>
        <ul class="guide-steps">
          <li><strong>容易刺痒、泛红：</strong>简化护肤，优先选无香料的保湿产品。</li>
          <li><strong>容易晒红或在意色沉：</strong>做好防晒，避免刻意日晒测试。</li>
          <li><strong>不适持续或加重：</strong>请皮肤科评估，不凭照片自行诊断。</li>
        </ul>
      </section>
      <footer class="guide-sources">
        肤质与护理要点摘编自何黎、李利《中国人面部皮肤分类与护肤指南》，《皮肤病与性病》2009 年第 31 卷第 4 期，14–15 页。2009 年资料仅供参考，不代表最新临床指南。防晒参考：<a href="https://www.aad.org/public/everyday-care/sun-protection/shade-clothing-sunscreen/how-to-select-sunscreen" target="_blank" rel="noopener noreferrer">美国皮肤科学会（AAD）</a>。
      </footer>
    </template>

    <HerlogSheet v-if="guideDetail !== null" :title="guideDetail === 0 ? '肤质分类详情' : '护理方法详情'" @close="guideDetail = null">
      <article class="guide-full">
        <p>以下为 2009 年指南内容，仅供参考。请勿自行尝试原文中的刺激试验或日晒测试。</p>
        <template v-for="(block, index) in guideSections[guideDetail]" :key="index">
          <h3 v-if="block.kind === 'heading'">{{ block.text }}</h3>
          <component v-else-if="block.kind === 'list'" :is="block.ordered ? 'ol' : 'ul'" class="guide-steps">
            <li v-for="item in block.items" :key="item">{{ item }}</li>
          </component>
          <div v-else-if="block.kind === 'table'" class="guide-table-scroll" tabindex="0" role="region" aria-label="不同肤质护理步骤对照表">
            <table class="guide-table guide-full-table">
              <thead><tr><th v-for="column in block.columns" :key="column" scope="col">{{ column }}</th></tr></thead>
              <tbody><tr v-for="row in block.rows" :key="row[0]">
                <th scope="row">{{ row[0] }}</th><td v-for="(cell, cellIndex) in row.slice(1)" :key="cellIndex">{{ cell }}</td>
              </tr></tbody>
            </table>
          </div>
          <p v-else>{{ block.text }}</p>
        </template>
        <footer class="guide-sources">来源：何黎、李利《中国人面部皮肤分类与护肤指南》，《皮肤病与性病》2009 年第 31 卷第 4 期，14–15 页。</footer>
      </article>
    </HerlogSheet>

    <HerlogSheet v-if="editor" title="护理日记" :context="formatDayLabel(editDay)" :busy="saving" @close="closeEditor">
        <view class="field-block">
          <view class="field-title">肤质自评</view>
          <view class="quiz">
            <view class="studio-muted">回想近一周，哪些部位比较容易泛油光？</view>
            <view class="chips">
              <SkinButton v-for="item in shineOptions" :key="item.code" class="journal-choice" :class="{ selected: shine === item.code }" :aria-pressed="shine === item.code" @click="shine = item.code">{{ item.label }}</SkinButton>
            </view>
            <view class="studio-muted">洁面后常觉得紧绷吗？</view>
            <view class="chips">
              <SkinButton class="journal-choice" :class="{ selected: tight === 'often' }" :aria-pressed="tight === 'often'" @click="tight = 'often'">经常</SkinButton>
              <SkinButton class="journal-choice" :class="{ selected: tight === 'rarely' }" :aria-pressed="tight === 'rarely'" @click="tight = 'rarely'">很少</SkinButton>
              <SkinButton class="studio-text" :disabled="!shine || !tight" @click="applyQuiz">使用自评结果</SkinButton>
            </view>
          </view>
          <view class="chips">
            <SkinButton v-for="(title, code) in typeNames" :key="code" class="journal-choice" :class="{ selected: edit.skin_type === code }" :aria-pressed="edit.skin_type === code" @click="edit.skin_type = edit.skin_type === code ? null : code">{{ title }}</SkinButton>
          </view>
        </view>
        <view class="field-block">
          <view class="field-title">舒适度</view>
          <view class="score-row">
            <SkinButton v-for="value in 5" :key="value" class="journal-score" :aria-label="comfortNames[value]" :aria-pressed="edit.comfort === value"
              :class="{ selected: edit.comfort === value }" @click="edit.comfort = edit.comfort === value ? null : value">
              <strong>{{ value }}</strong><small>{{ comfortNames[value] }}</small>
            </SkinButton>
          </view>
        </view>
        <view class="field-block">
          <view class="field-title">今天的感受</view>
          <view class="chips">
            <SkinButton v-for="(label, code) in sensationNames" :key="code" class="journal-choice" :class="{ selected: edit.sensations.includes(code) }" :aria-pressed="edit.sensations.includes(code)" @click="toggleSensation(code)">{{ label }}</SkinButton>
          </view>
        </view>
        <view class="field-block">
          <view class="field-title">做过的护理</view>
          <view class="chips">
            <SkinButton v-for="(label, code) in routineNames" :key="code" class="journal-choice" :class="{ selected: edit.routine.includes(code) }" :aria-pressed="edit.routine.includes(code)" @click="toggleRoutine(code)">{{ label }}</SkinButton>
          </view>
          <textarea v-model="editNote" aria-label="仅自己可见的备注" class="journal-note" placeholder="备注 · 仅自己可见" maxlength="400" />
        </view>
        <view v-if="editorError" class="studio-alert" role="alert">{{ editorError }}</view>
        <template #actions>
          <SkinButton v-if="editingExisting" class="studio-text" :disabled="saving" @click="removeEntry">删除</SkinButton>
          <SkinButton class="primary" :disabled="saving" @click="submit">{{ saving ? '保存中…' : '保存日记' }}</SkinButton>
        </template>
    </HerlogSheet>
  </view>
</template>

<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import SkinButton from '../../components/H5Button'
import HerlogHeading from '../../components/HerlogHeading.vue'
import HerlogIcon from '../../components/HerlogIcon.vue'
import HerlogMascot from '../../components/HerlogMascot.vue'
import HerlogSheet from '../../components/HerlogSheet.vue'
import guideSource from './skin-care-guide.md?raw'
import ObservationCopy from './ObservationCopy.vue'
import PrivateSkinImage from './PrivateSkinImage.vue'
import { SKIN_SAMPLES } from './skinSamples'
import { formatDayLabel, formatMoment, formatMonthLabel, monthGrid, shanghaiDayKey, shiftMonth, startOfMonth, todayString } from '../../shared/dates'
import { groupSkinDays, selfAssessedSkinType, skinMonthRange } from '../../shared/skin'
import { listObservations } from '../../services/skinService'
import { deleteJournal, latestJournal, listJournal, saveJournal } from '../../services/wellnessService'
import { currentEpoch } from '../../services/httpClient'
import type { SkinSummaryItem } from '../../services/types'
import type { JournalDay, JournalInput, SkinRoutine, SkinSensation, SkinType } from '../../services/wellnessService'

const props = defineProps<{ latest: SkinSummaryItem | null; photoLoading: boolean; photoError: boolean }>()
const emit = defineEmits<{ capture: []; history: [compare: boolean, day?: string]; 'refresh-photo': [] }>()
const tabs = [{ key: 'today', label: '今日' }, { key: 'calendar', label: '日历' }, { key: 'care', label: '护理指南' }] as const
type Tab = typeof tabs[number]['key']
const tab = ref<Tab>('today')
const guideDetail = ref<0 | 1 | null>(null)
const guideSections = guideSource.split(/^## [12] .+$/m).slice(1).map(section =>
  section.trim().split(/\r?\n\s*\r?\n/).map(block => {
    const lines = block.replace(/\*\*|`/g, '').split(/\r?\n/)
    if (lines[0].startsWith('|')) {
      const [columns, , ...rows] = lines.map(line => line.trim().split('|').slice(1, -1).map(cell => cell.trim()))
      return { kind: 'table' as const, columns, rows }
    }
    if (lines.every(line => /^(?:- |\d+\. )/.test(line))) {
      return { kind: 'list' as const, ordered: !lines[0].startsWith('- '), items: lines.map(line => line.replace(/^(?:- |\d+\. )/, '')) }
    }
    if (lines[0].startsWith('###')) return { kind: 'heading' as const, text: lines[0].replace(/^#+ /, '') }
    return { kind: 'paragraph' as const, text: lines.join('\n') }
  })
)
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
const selectedPhotos = computed(() => calendarLoading.value || calendarError.value ? [] : photoDays.value.get(dateSelected.value) ?? [])
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
  if (value === 'calendar') {
    const latestPhotoDay = props.latest ? shanghaiDayKey(props.latest.captured_at) : ''
    dateSelected.value = [latestEntry.value?.day ?? '', latestPhotoDay].sort().at(-1) || today
    month.value = startOfMonth(dateSelected.value)
    void loadMonth()
  }
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
function openEditor(day: string, prefillSun = false) {
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
