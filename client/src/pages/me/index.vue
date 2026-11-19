<template>
  <view class="hr-page hr-tab-page profile-page">
    <HerlogHeading title="我的" description="给自己留一方小天地。" />
    <view class="identity card">
      <svg class="identity-icon" viewBox="0 0 56 56" aria-hidden="true">
        <rect width="56" height="56" rx="17" :fill="avatar.paper" />
        <path d="M28 46c0-8 1-14 0-22m0 17c-7 0-11-4-12-9 6 0 10 3 12 7m0 4c2-6 6-9 12-10-1 6-5 10-12 10" fill="#78927c" stroke="#78927c" stroke-width="1.4" stroke-linecap="round" />
        <path :d="avatar.petals" :fill="avatar.ink" />
        <circle cx="28" cy="23" r="2.8" fill="#fff0b8" />
      </svg>
      <view class="identity-copy">
        <view class="identity-name">{{ auth.username || '个人账号' }}</view>
        <view class="muted">账号资料</view>
      </view>
    </view>
    <H5Form class="card profile-card" @submit.prevent="save">
      <h2 class="hr-section-title">个人资料</h2>
      <view class="profile-row">
        <H5Label class="hr-field-label" for="profile-birthday">生日</H5Label>
        <H5Input id="profile-birthday" v-model="birthday" class="field" type="date" :max="today" />
      </view>
      <view class="profile-row">
        <H5Label class="hr-field-label" for="profile-height">身高 <small>厘米</small></H5Label>
        <H5Input id="profile-height" v-model="heightCm" class="field" inputmode="decimal" placeholder="选填" />
        <view class="muted">用于体重明细中的 BMI 计算。</view>
      </view>
      <view class="profile-row">
        <H5Label class="hr-field-label" for="profile-phone">电话</H5Label>
        <H5Input id="profile-phone" v-model="contactPhone" class="field" type="tel" maxlength="32" placeholder="选填" />
      </view>
      <text v-if="error" class="error" role="alert">{{ error }}</text>
      <H5Button type="submit" class="primary" :disabled="saving">{{ saving ? '保存中…' : '保存资料' }}</H5Button>
      <view v-if="saved" class="ok" role="status">资料已更新</view>
    </H5Form>
    <view class="card profile-card">
      <h2 class="hr-section-title">登录状态</h2>
      <view class="muted">退出登录后，重新登录同一账号即可查看自己的记录。</view>
      <H5Button class="ghost" @click="logout">退出登录</H5Button>
    </view>
    <TabBar current="/pages/me/index" />
  </view>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue'
import { onShow } from '@dcloudio/uni-app'
import H5Button from '../../components/H5Button'
import H5Form, { H5Label } from '../../components/H5Form'
import H5Input from '../../components/H5Input'
import HerlogHeading from '../../components/HerlogHeading.vue'
import TabBar from '../../components/TabBar.vue'
import { todayString } from '../../shared/dates'
import { useAuthStore } from '../../stores/auth'
import { ApiRequestError, StaleSessionError } from '../../services/httpClient'
import { getProfile, updateProfile } from '../../services/profileService'

const auth = useAuthStore()
const avatars = [
  { paper: '#f9e5eb', ink: '#b8607a', petals: 'M28 23C13 28 14 15 23 17C19 7 35 7 33 17C43 15 43 29 28 23Z' },
  { paper: '#eee8f6', ink: '#8c74ae', petals: 'M28 27C14 27 15 13 20 14L25 18C24 9 33 9 32 18L37 14C42 17 40 27 28 27Z' },
  { paper: '#f9ebdc', ink: '#be7949', petals: 'M28 26C20 30 16 25 20 21C14 16 20 12 25 16C23 8 33 8 32 16C38 12 42 18 37 21C42 26 36 30 28 26Z' },
  { paper: '#e7f1eb', ink: '#537d76', petals: 'M28 28C18 26 18 21 22 20C17 15 22 11 26 15C26 6 34 9 32 16C38 13 41 18 36 22C39 26 34 29 28 28Z' },
]
const avatar = computed(() => {
  const digit = auth.member?.customer_id.slice(-1) ?? ''
  return avatars[(Number.parseInt(digit, 16) || 0) % avatars.length]
})
const today = todayString()
const birthday = ref('')
const heightCm = ref('')
const contactPhone = ref('')
const error = ref('')
const saved = ref(false)
const saving = ref(false)

async function load() {
  try {
    const profile = await getProfile()
    birthday.value = profile.birthday ?? ''
    heightCm.value = profile.height_cm === null ? '' : String(Number(profile.height_cm))
    contactPhone.value = profile.contact_phone ?? ''
  } catch (failure) {
    if (failure instanceof StaleSessionError) {
      return
    }
    uni.showToast({
      title: failure instanceof ApiRequestError ? failure.message : '资料加载失败',
      icon: 'none'
    })
  }
}

async function save() {
  if (saving.value) {
    return
  }
  error.value = ''
  saved.value = false
  const height = heightCm.value.trim()
  if (height) {
    const value = Number(height)
    if (!Number.isFinite(value) || value <= 0) {
      error.value = '身高需为有效正数'
      return
    }
  }
  if (birthday.value && birthday.value > today) {
    error.value = '生日不能晚于今天'
    return
  }
  saving.value = true
  try {
    const profile = await updateProfile({
      birthday: birthday.value || null,
      height_cm: height || null,
      contact_phone: contactPhone.value.trim() || null
    })
    birthday.value = profile.birthday ?? ''
    heightCm.value = profile.height_cm === null ? '' : String(Number(profile.height_cm))
    contactPhone.value = profile.contact_phone ?? ''
    saved.value = true
  } catch (failure) {
    error.value = failure instanceof ApiRequestError ? failure.message : '保存失败，请稍后重试'
  } finally {
    saving.value = false
  }
}

async function logout() {
  await auth.logout()
  uni.reLaunch({ url: '/pages/login/index' })
}

onShow(load)
</script>

<style scoped>
.identity { display: flex; gap: 13px; align-items: center; padding: 15px; background: var(--hr-rose-soft); }
.identity-icon {
  display: block; flex: 0 0 56px; width: 56px; height: 56px;
}
.identity-copy { min-width: 0; }
.identity-name { font-weight: 700; font-size: 19px; overflow-wrap: anywhere; }
.profile-card { display: grid; gap: 10px; }
.profile-card h2 { margin: 0; }
.profile-row { padding: 10px 0 8px; border-bottom: 1px solid var(--hr-line); }
.profile-row .field { margin-bottom: 4px; }
small { font-size: 12px; color: var(--hr-ink-2); font-weight: 400; }
.ok { color: var(--hr-taupe); font-size: 13px; }
input[type=date]:not(:valid) { color: var(--hr-ink-2); }
</style>
