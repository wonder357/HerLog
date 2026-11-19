<template>
  <view class="hr-page hr-tab-page profile-page">
    <HerlogHeading title="我的" />
    <view class="identity card">
      <view class="identity-icon" aria-hidden="true"><HerlogIcon name="me" /></view>
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
import { ref } from 'vue'
import { onShow } from '@dcloudio/uni-app'
import H5Button from '../../components/H5Button'
import H5Form, { H5Label } from '../../components/H5Form'
import H5Input from '../../components/H5Input'
import HerlogHeading from '../../components/HerlogHeading.vue'
import HerlogIcon from '../../components/HerlogIcon.vue'
import TabBar from '../../components/TabBar.vue'
import { todayString } from '../../shared/dates'
import { useAuthStore } from '../../stores/auth'
import { ApiRequestError, StaleSessionError } from '../../services/httpClient'
import { getProfile, updateProfile } from '../../services/profileService'

const auth = useAuthStore()
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
.identity { display: flex; gap: 13px; align-items: center; padding: 15px; }
.identity-icon {
  display: grid; place-items: center; flex: 0 0 52px; height: 52px; border-radius: 16px;
  color: var(--hr-rose-deep); background: var(--hr-rose-soft);
}
.identity-icon svg { width: 27px; height: 27px; }
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
