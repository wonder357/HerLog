<template>
  <view class="hr-page hr-tab-page profile-page">
    <HerlogHeading title="我的" />
    <section class="card identity">
      <span class="identity-icon">
        <img v-if="avatarUrl" :src="avatarUrl" alt="个人头像" />
        <svg v-else viewBox="0 0 56 56" aria-hidden="true">
          <rect width="56" height="56" rx="17" :fill="avatar.paper" />
          <path d="M28 46c0-8 1-14 0-22m0 17c-7 0-11-4-12-9 6 0 10 3 12 7m0 4c2-6 6-9 12-10-1 6-5 10-12 10" fill="#99786e" stroke="#99786e" stroke-width="1.4" stroke-linecap="round" />
          <path :d="avatar.petals" :fill="avatar.ink" />
          <circle cx="28" cy="23" r="2.8" fill="#fff0b8" />
        </svg>
      </span>
      <div class="identity-copy"><strong>{{ auth.username || '个人账号' }}</strong><span>个人资料</span></div>
      <H5Button class="hr-action" @click="openProfile">编辑资料 ›</H5Button>
    </section>

    <section class="card bmi-card" aria-labelledby="bmi-title">
      <view class="bmi-head">
        <h2 id="bmi-title" class="hr-section-title">BMI 摘要</h2>
        <HerlogMascot class="bmi-mascot" pose="done" :size="64" alt="" />
      </view>
      <p v-if="summaryLoading" class="muted" role="status">正在读取摘要…</p>
      <div v-else-if="summaryError" class="inline-state" role="alert">
        <span>暂时无法读取摘要。</span><H5Button class="hr-action" @click="loadSummary">重试</H5Button>
      </div>
      <template v-else-if="summary">
        <strong v-if="bmi?.status === 'available'" class="bmi-value">{{ bmi.value }}</strong>
        <p v-if="bmi?.status === 'available'" class="muted">按 {{ bmi.height_cm }} cm 和 {{ formatDayLabel(bmi.weight_day!) }}的最新体重计算。</p>
        <p v-else class="muted">{{ bmi?.status === 'missing_height' ? '补充身高后即可计算。' : bmi?.status === 'missing_weight' ? '记录一次体重后即可计算。' : '添加身高和体重后即可计算。' }}</p>
        <div v-if="bmi?.status !== 'available'" class="inline-actions">
          <H5Button v-if="bmi?.status !== 'missing_weight'" class="ghost" @click="openProfile">补身高</H5Button>
          <H5Button v-if="bmi?.status !== 'missing_height'" class="ghost" @click="weightVisible = true">记体重</H5Button>
        </div>
      </template>
      <p class="muted bmi-note">不反映体脂和肌肉分布。</p>
    </section>

    <section class="card" aria-labelledby="archive-title">
      <h2 id="archive-title" class="hr-section-title">健康档案</h2>
      <H5Button v-for="item in archive" :key="item.page" class="settings-row" @click="go(item.page)">
        <span class="archive-label"><HerlogIcon :name="item.page" />{{ item.label }}</span>
        <span class="row-value">{{ summaryLoading ? '读取中…' : summaryError ? '暂不可用' : item.day || '尚无记录' }} <span aria-hidden="true">›</span></span>
      </H5Button>
    </section>

    <section class="card" aria-labelledby="cycle-settings">
      <h2 id="cycle-settings" class="hr-section-title">周期与习惯</h2>
      <H5Button class="settings-row" @click="modeSettings = true">
        <span>周期模式</span><span class="row-value">{{ cyclePreference.preference ? cyclePreference.mode === 'trying_to_conceive' ? '备孕' : '经期' : '设置' }} ›</span>
      </H5Button>
      <p v-if="cyclePreference.mode === 'trying_to_conceive'" class="muted mode-note">{{ fertilityNotice }}。</p>
      <H5Button class="settings-row" @click="openPreferences('reminders')">
        <span>提醒偏好</span><span class="row-value">设置 ›</span>
      </H5Button>
      <H5Button class="settings-row" @click="openPreferences('recording')">
        <span>记录习惯与首页</span><span class="row-value">设置 ›</span>
      </H5Button>
    </section>

    <section class="card" aria-labelledby="privacy-settings">
      <h2 id="privacy-settings" class="hr-section-title">账号与隐私</h2>
      <H5Button class="settings-row" @click="panel = 'login-phone'">
        <span>登录手机号</span><span class="row-value">{{ auth.member?.verified_phone_hint ?? '未绑定' }} ›</span>
      </H5Button>
      <H5Button class="settings-row" @click="panel = 'privacy'"><span>隐私说明</span><span class="row-value" aria-hidden="true">›</span></H5Button>
      <H5Button class="settings-row" @click="panel = 'password'"><span>修改密码</span><span class="row-value" aria-hidden="true">›</span></H5Button>
      <H5Button class="settings-row" @click="panel = 'clear'"><span>清除本机缓存</span><span class="row-value" aria-hidden="true">›</span></H5Button>
      <div class="settings-row subtle"><span>数据导出</span><span class="row-value">暂未开放</span></div>
      <H5Button class="settings-row logout" :disabled="loggingOut" @click="panel = 'logout'">退出登录</H5Button>
    </section>

    <HerlogSheet v-if="panel === 'profile'" title="编辑资料" :busy="profileSaving" @close="closeProfile">
      <p v-if="profileLoading" class="muted" role="status">正在读取资料…</p>
      <div v-else-if="!profile" class="inline-state" role="alert">
        <span>{{ profileError }}</span><H5Button class="hr-action" @click="loadProfile">重试</H5Button>
      </div>
      <H5Form v-else id="profile-form" @submit.prevent="saveProfile">
        <PrivatePhotoEditor v-model="avatarChange" v-model:processing="avatarProcessing" label="头像" avatar
          :saved-path="profile.has_avatar ? avatarPath : undefined" :disabled="profileSaving" />
        <H5Label class="hr-field-label" for="profile-username">用户名</H5Label>
        <H5Input id="profile-username" :model-value="profile.username" class="field" readonly />
        <H5Label class="hr-field-label" for="profile-birthday">生日（选填）</H5Label>
        <H5Input id="profile-birthday" v-model="birthday" class="field" type="date" :max="today" :disabled="profileSaving" />
        <p v-if="birthdayError" class="error" role="alert">{{ birthdayError }}</p>
        <H5Label class="hr-field-label" for="profile-height">身高（cm，选填）</H5Label>
        <H5Input id="profile-height" v-model="height" class="field" inputmode="decimal" placeholder="例如 165" :disabled="profileSaving" />
        <p v-if="heightError" class="error" role="alert">{{ heightError }}</p>
        <H5Label class="hr-field-label" for="profile-phone">联系电话（选填）</H5Label>
        <H5Input id="profile-phone" v-model="phone" class="field" type="tel" maxlength="32" autocomplete="tel" :disabled="profileSaving" />
        <p v-if="profileError" class="error" role="alert">{{ profileError }}</p>
      </H5Form>
      <template #actions>
        <H5Button class="primary" type="submit" form="profile-form" :disabled="profileLoading || profileSaving || avatarProcessing || !profile">
          {{ profileSaving ? '保存中…' : '保存资料' }}
        </H5Button>
      </template>
    </HerlogSheet>

    <HerlogSheet v-if="panel === 'reminders' || panel === 'recording'" :title="panel === 'reminders' ? '提醒偏好' : '记录习惯与首页'"
      :busy="preferenceSaving" @close="panel = null">
      <p v-if="preferenceLoading" class="muted" role="status">正在读取设置…</p>
      <template v-else-if="panel === 'reminders' && reminders">
        <p class="muted">当前仅保存偏好，暂不会发送通知。</p>
        <H5Button v-for="option in reminderOptions" :key="option.key" class="settings-row" role="switch"
          :aria-checked="reminders[option.key]" :disabled="preferenceSaving" @click="toggleReminder(option.key)">
          <span>{{ option.label }}</span><span class="switch" aria-hidden="true" />
        </H5Button>
      </template>
      <template v-else-if="panel === 'recording' && recording">
        <H5Label class="hr-field-label" for="recording-goal">每周记录天数</H5Label>
        <select id="recording-goal" class="field" :value="recording.weekly_record_days_target ?? ''" :disabled="preferenceSaving"
          @change="saveGoal">
          <option value="">不设置目标</option>
          <option v-for="day in 7" :key="day" :value="day">{{ day }} 天</option>
        </select>
        <p class="muted">同一天记录多项，仍计为一天。</p>
        <H5Button v-for="option in recordingOptions" :key="option.key" class="settings-row" role="switch"
          :aria-checked="recording[option.key]" :disabled="preferenceSaving" @click="toggleRecording(option.key)">
          <span>{{ option.label }}</span><span class="switch" aria-hidden="true" />
        </H5Button>
      </template>
      <div v-if="preferenceError" class="inline-state" role="alert">
        <span>{{ preferenceError }}</span><H5Button class="hr-action" @click="retryPreference">重试</H5Button>
      </div>
      <p v-if="preferenceSaved" class="muted" role="status">设置已保存</p>
      <template #actions><H5Button class="primary" :disabled="preferenceSaving" @click="panel = null">完成</H5Button></template>
    </HerlogSheet>

    <HerlogSheet v-if="panel === 'privacy'" title="隐私说明" @close="panel = null">
      <ul class="privacy-copy">
        <li>「查记录」仅在当前登录账号下读取已保存的信息。「DeepSeek 对话」会把本次对话中该模式的文字发送给 DeepSeek。</li>
        <li>皮肤照片的使用范围在分析前说明，确认保存后才进入账号历史。查看照片需要登录。</li>
        <li>头像、体重和运动照片仅自己可见，可在对应记录中更换或移除。</li>
        <li>手机号验证使用短信服务商投递，登录手机号和资料里的联系电话分别管理。</li>
        <li>清除本机缓存或退出登录会清理本机浏览数据，账号内已保存的记录仍可在下次登录后查看。</li>
      </ul>
      <template #actions><H5Button class="primary" @click="panel = null">完成</H5Button></template>
    </HerlogSheet>
    <HerlogSheet v-if="panel === 'clear' || panel === 'logout'" :title="panel === 'clear' ? '清除本机缓存？' : '退出当前账号？'"
      :busy="loggingOut" @close="panel = null">
      <p class="muted">{{ panel === 'clear' ? '将清除临时图片和页面副本。你仍保持登录，账号记录会保留。' : '会清除本机登录信息和临时数据，已保存的账号记录会保留。' }}</p>
      <template #actions>
        <H5Button class="ghost" :disabled="loggingOut" @click="panel = null">取消</H5Button>
        <H5Button class="primary" :disabled="loggingOut" @click="panel === 'clear' ? clearCache() : logout()">
          {{ panel === 'clear' ? '清除' : loggingOut ? '正在退出…' : '退出' }}
        </H5Button>
      </template>
    </HerlogSheet>
    <PasswordSheet v-if="panel === 'password'" @close="panel = null" @saved="passwordSaved" />
    <BindPhoneSheet v-if="panel === 'login-phone'" @close="panel = null" @saved="phoneBound" />
    <WeightForm :visible="weightVisible" @close="weightVisible = false" @saved="weightSaved" />
    <CycleModeSheet v-if="modeSettings" @close="modeSettings = false" @changed="modeChanged" />
    <TabBar current="/pages/me/index" />
  </view>
</template>

<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { onHide, onShow } from '@dcloudio/uni-app'
import H5Button from '../../components/H5Button'
import H5Form, { H5Label } from '../../components/H5Form'
import H5Input from '../../components/H5Input'
import HerlogHeading from '../../components/HerlogHeading.vue'
import HerlogIcon from '../../components/HerlogIcon.vue'
import HerlogMascot from '../../components/HerlogMascot.vue'
import HerlogSheet from '../../components/HerlogSheet.vue'
import TabBar from '../../components/TabBar.vue'
import WeightForm from '../../components/WeightForm.vue'
import PrivatePhotoEditor from '../../components/PrivatePhotoEditor.vue'
import { usePrivatePhoto } from '../../components/usePrivatePhoto'
import CycleModeSheet from '../period/CycleModeSheet.vue'
import PasswordSheet from './PasswordSheet.vue'
import BindPhoneSheet from './BindPhoneSheet.vue'
import { useAuthStore } from '../../stores/auth'
import { useCyclePreference } from '../../stores/cyclePreference'
import { ApiRequestError, currentEpoch } from '../../services/httpClient'
import { getProfile, updateProfile } from '../../services/profileService'
import { avatarPath } from '../../services/privatePhotoService'
import type { PrivatePhotoPayload } from '../../services/privatePhotoService'
import { fetchHealthSummary, fetchRecordingPreferences, fetchReminders, saveRecordingPreferences, saveReminders } from '../../services/homeService'
import type { HealthSummary, RecordingPreferences, ReminderSettings } from '../../services/homeService'
import type { ProfileInfo } from '../../services/types'
import { formatDayLabel, todayString } from '../../shared/dates'
import { fertilityNotice } from '../../shared/fertility'

type PreferencePanel = 'reminders' | 'recording'
const auth = useAuthStore()
const avatars = [
  { paper: '#f9e5eb', ink: '#b8607a', petals: 'M28 23C13 28 14 15 23 17C19 7 35 7 33 17C43 15 43 29 28 23Z' },
  { paper: '#eee8f6', ink: '#8c74ae', petals: 'M28 27C14 27 15 13 20 14L25 18C24 9 33 9 32 18L37 14C42 17 40 27 28 27Z' },
  { paper: '#f9ebdc', ink: '#be7949', petals: 'M28 26C20 30 16 25 20 21C14 16 20 12 25 16C23 8 33 8 32 16C38 12 42 18 37 21C42 26 36 30 28 26Z' },
  { paper: '#f3eae7', ink: '#896156', petals: 'M28 28C18 26 18 21 22 20C17 15 22 11 26 15C26 6 34 9 32 16C38 13 41 18 36 22C39 26 34 29 28 28Z' },
]
const avatar = computed(() => {
  const digit = auth.member?.customer_id.slice(-1) ?? ''
  return avatars[(Number.parseInt(digit, 16) || 0) % avatars.length]
})
const cyclePreference = useCyclePreference()
const today = ref(todayString())
const summary = ref<HealthSummary | null>(null)
const pageVisible = ref(false)
const { url: avatarUrl, reload: reloadAvatar } = usePrivatePhoto(() =>
  pageVisible.value && summary.value?.has_avatar ? avatarPath : undefined
)
const avatarChange = ref<PrivatePhotoPayload | null>()
const avatarProcessing = ref(false)
const summaryLoading = ref(false)
const summaryError = ref(false)
const bmi = computed(() => summary.value?.bmi)
const profile = ref<ProfileInfo | null>(null)
const birthday = ref('')
const height = ref('')
const phone = ref('')
const profileLoading = ref(false)
const profileSaving = ref(false)
const profileError = ref('')
const birthdayError = ref('')
const heightError = ref('')
const reminders = ref<ReminderSettings | null>(null)
const recording = ref<RecordingPreferences | null>(null)
const preferenceLoading = ref(false)
const preferenceSaving = ref(false)
const preferenceSaved = ref(false)
const preferenceError = ref('')
const panel = ref<'profile' | 'password' | 'login-phone' | 'privacy' | 'clear' | 'logout' | PreferencePanel | null>(null)
const modeSettings = ref(false)
const weightVisible = ref(false)
const loggingOut = ref(false)
let summarySequence = 0
let formSequence = 0
let preferenceSequence = 0
let lastWrite: (() => Promise<void>) | null = null

const reminderOptions = [
  { key: 'period_reminder_enabled', label: '经期提醒' }, { key: 'record_reminder_enabled', label: '记录提醒' }
] as const
const recordingOptions = [
  { key: 'show_focus', label: '首页显示今日聚焦' }, { key: 'show_summary', label: '首页显示健康摘要' },
  { key: 'show_questions', label: '首页显示问题建议' }
] as const
const archive = computed(() => [
  { page: 'period', label: '最近经期开始', day: summary.value?.latest_period_start },
  { page: 'weight', label: '最近体重测量', day: summary.value?.latest_weight_day },
  { page: 'skin', label: '最近皮肤观察', day: summary.value?.latest_skin_observation_day }
] as const)

async function loadSummary() {
  const epoch = currentEpoch()
  const sequence = ++summarySequence
  const active = () => epoch === currentEpoch() && sequence === summarySequence
  summaryLoading.value = true
  summaryError.value = false
  try {
    const result = await fetchHealthSummary()
    if (active()) summary.value = result
  } catch {
    if (active()) summaryError.value = true
  } finally {
    if (active()) summaryLoading.value = false
  }
}

function applyProfile(value: ProfileInfo) {
  profile.value = value
  birthday.value = value.birthday ?? ''
  height.value = value.height_cm === null ? '' : String(Number(value.height_cm))
  phone.value = value.contact_phone ?? ''
}

async function loadProfile() {
  const epoch = currentEpoch()
  const sequence = ++formSequence
  const active = () => epoch === currentEpoch() && sequence === formSequence && panel.value === 'profile'
  profileLoading.value = true
  profileError.value = ''
  try {
    const result = await getProfile()
    if (active()) applyProfile(result)
  } catch {
    if (active()) profileError.value = '暂时无法读取资料。'
  } finally {
    if (active()) profileLoading.value = false
  }
}

function openProfile() {
  avatarChange.value = undefined
  birthdayError.value = heightError.value = profileError.value = ''
  profile.value = null
  panel.value = 'profile'
  void loadProfile()
}

function closeProfile() {
  panel.value = null
  avatarChange.value = undefined
}

async function saveProfile() {
  if (profileSaving.value || avatarProcessing.value) return
  const value = height.value.trim()
  birthdayError.value = birthday.value && birthday.value > today.value ? '生日不能晚于今天。' : ''
  heightError.value = value && (!/^\d{1,3}(\.\d{1,2})?$/.test(value) || Number(value) <= 0)
    ? '请输入大于 0 的厘米数，最多两位小数。' : ''
  if (birthdayError.value || heightError.value) return
  const epoch = currentEpoch()
  profileSaving.value = true
  profileError.value = ''
  try {
    const result = await updateProfile({
      birthday: birthday.value || null,
      height_cm: value || null,
      contact_phone: phone.value.trim() || null,
      ...(avatarChange.value !== undefined ? { avatar: avatarChange.value } : {})
    })
    if (epoch !== currentEpoch()) return
    applyProfile(result)
    if (summary.value) {
      const replaced = summary.value.has_avatar && result.has_avatar && avatarChange.value !== undefined
      summary.value = { ...summary.value, has_avatar: result.has_avatar }
      if (replaced) void reloadAvatar()
    }
    closeProfile()
    uni.showToast({ title: '资料已保存', icon: 'none' })
    void loadSummary()
  } catch (failure) {
    if (epoch === currentEpoch()) profileError.value = failure instanceof ApiRequestError ? failure.message : '保存失败，请重试。'
  } finally {
    if (epoch === currentEpoch()) profileSaving.value = false
  }
}

function openPreferences(kind: PreferencePanel) {
  panel.value = kind
  lastWrite = null
  void loadPreferences(kind)
}

async function loadPreferences(kind: PreferencePanel) {
  const epoch = currentEpoch()
  const sequence = ++preferenceSequence
  const active = () => epoch === currentEpoch() && sequence === preferenceSequence && panel.value === kind
  preferenceLoading.value = true
  preferenceError.value = ''
  preferenceSaved.value = false
  try {
    if (kind === 'reminders') {
      const value = await fetchReminders()
      if (active()) reminders.value = value
    } else {
      const value = await fetchRecordingPreferences()
      if (active()) recording.value = value
    }
  } catch {
    if (active()) preferenceError.value = '暂时无法读取设置。'
  } finally {
    if (active()) preferenceLoading.value = false
  }
}

async function writePreference(operation: (epoch: number) => Promise<void>) {
  if (preferenceSaving.value) return
  const epoch = currentEpoch()
  preferenceSaving.value = true
  preferenceError.value = ''
  preferenceSaved.value = false
  lastWrite = () => writePreference(operation)
  try {
    await operation(epoch)
    if (epoch === currentEpoch()) {
      preferenceSaved.value = true
      lastWrite = null
    }
  } catch {
    if (epoch === currentEpoch()) preferenceError.value = '设置未保存，请重试。'
  } finally {
    if (epoch === currentEpoch()) preferenceSaving.value = false
  }
}

function toggleReminder(key: typeof reminderOptions[number]['key']) {
  const enabled = !reminders.value?.[key]
  void writePreference(async epoch => {
    const result = await saveReminders({ [key]: enabled })
    if (epoch === currentEpoch()) reminders.value = result
  })
}

function writeRecording(values: Partial<RecordingPreferences>) {
  void writePreference(async epoch => {
    const result = await saveRecordingPreferences(values)
    if (epoch === currentEpoch()) recording.value = result
  })
}

function toggleRecording(key: typeof recordingOptions[number]['key']) {
  writeRecording({ [key]: !recording.value?.[key] })
}

function saveGoal(event: Event) {
  const select = event.target as HTMLSelectElement
  const desired = select.value ? Number(select.value) : null
  select.value = String(recording.value?.weekly_record_days_target ?? '')
  writeRecording({ weekly_record_days_target: desired })
}

function retryPreference() {
  if (lastWrite) void lastWrite()
  else if (panel.value === 'reminders' || panel.value === 'recording') void loadPreferences(panel.value)
}

function go(page: 'period' | 'weight' | 'skin') {
  uni.switchTab({ url: '/pages/' + page + '/index' })
}

function modeChanged() {
  modeSettings.value = false
  go('period')
}

function weightSaved() {
  weightVisible.value = false
  void loadSummary()
  uni.showToast({ title: '体重已保存', icon: 'none' })
}

function reset() {
  summarySequence += 1
  formSequence += 1
  preferenceSequence += 1
  summary.value = profile.value = reminders.value = recording.value = null
  panel.value = null
  avatarChange.value = undefined
  modeSettings.value = weightVisible.value = false
  summaryLoading.value = profileLoading.value = profileSaving.value = preferenceLoading.value = preferenceSaving.value = false
  loggingOut.value = false
  birthday.value = height.value = phone.value = ''
  lastWrite = null
}

function clearCache() {
  auth.resetPrivateCache()
  uni.reLaunch({ url: '/pages/me/index', success: () => uni.showToast({ title: '本机缓存已清除', icon: 'none' }) })
}

async function logout() {
  if (loggingOut.value) return
  loggingOut.value = true
  await auth.logout()
  if (!auth.isLoggedIn) uni.reLaunch({ url: '/pages/login/index' })
}

function phoneBound() {
  panel.value = null
  uni.showToast({ title: '手机号已验证', icon: 'none' })
}

function passwordSaved() {
  auth.endLocalSession()
  uni.reLaunch({ url: '/pages/login/index', success: () => uni.showToast({ title: '密码已更新，请重新登录', icon: 'none' }) })
}

watch(() => [auth.token, auth.privateCacheRevision], reset, { flush: 'sync' })
onHide(() => { closeProfile(); pageVisible.value = weightVisible.value = modeSettings.value = false })
onShow(() => {
  if (!auth.isLoggedIn) {
    uni.reLaunch({ url: '/pages/login/index' })
    return
  }
  today.value = todayString()
  pageVisible.value = true
  void loadSummary()
  void cyclePreference.load()
})
</script>

<style scoped>
.identity { display:flex; align-items:center; gap:11px; }
.identity-icon { display:block; flex:0 0 56px; width:56px; height:56px; border-radius:17px; }
.identity-icon svg,.identity-icon img { display:block; width:100%; height:100%; }
.identity-icon img { object-fit:cover; border-radius:inherit; }
.identity-copy { min-width:0; flex:1; overflow-wrap:anywhere; }
.identity-copy strong,.identity-copy span { display:block; }
.identity-copy span { color:var(--hr-ink-2); font-size:13px; }
.identity .hr-action { flex-shrink:0; padding-inline:0; }
.bmi-card { background:linear-gradient(130deg,var(--hr-rose-soft),var(--hr-peach)); }
.bmi-head { display:flex; align-items:center; justify-content:space-between; gap:10px; }
.bmi-mascot { flex:none; }
.profile-page h2 { margin:0 0 6px; }
.bmi-value { display:block; margin:6px 0; color:var(--hr-ink); font:35px/1 var(--hr-serif); font-variant-numeric:tabular-nums; }
.bmi-card .muted { margin:5px 0; }
.bmi-note { line-height:1.5; }
.inline-actions { display:flex; gap:8px; margin:9px 0 7px; }
.inline-actions .ghost { width:auto; }
.inline-state { display:flex; gap:6px; align-items:center; justify-content:space-between; font-size:13px; }
.inline-state span { color:var(--hr-danger); }
.settings-row { display:flex; width:100%; min-height:46px; gap:8px; align-items:center; justify-content:space-between; padding:8px 0; text-align:left; border:0; border-bottom:1px solid var(--hr-line); background:transparent; color:var(--hr-ink); font-size:14px; }
.settings-row:last-child { border-bottom:0; }
.archive-label { display:flex; align-items:center; gap:7px; }
.archive-label svg { width:17px; height:17px; flex-shrink:0; color:var(--hr-rose-deep); }
.row-value { flex-shrink:0; color:var(--hr-ink-2); text-align:right; font-size:13px; white-space:nowrap; }
.subtle { color:var(--hr-ink-2); }
.settings-row.logout { color:var(--hr-danger); }
.mode-note { margin:4px 0; }
.switch { position:relative; width:36px; height:21px; flex-shrink:0; border:1px solid var(--hr-line-strong); border-radius:20px; background:var(--hr-paper-deep); }
.switch::after { content:''; position:absolute; left:3px; top:3px; width:13px; height:13px; border-radius:50%; background:var(--hr-taupe); }
[aria-checked='true'] .switch { background:var(--hr-rose); border-color:var(--hr-rose); }
[aria-checked='true'] .switch::after { left:auto; right:3px; background:var(--hr-surface); }
.privacy-copy { padding-left:18px; font-size:14px; line-height:1.6; }
.privacy-copy li + li { margin-top:8px; }
</style>
