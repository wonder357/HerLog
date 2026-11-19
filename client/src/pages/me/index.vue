<template>
  <view class="page">
    <view class="hero me-hero">
      <view class="h-title">我的</view>
      <view class="profile">
        <view class="avatar">{{ avatarText }}</view>
        <view class="profile-info">
          <view class="name">{{ displayName }}</view>
          <view class="user">@{{ auth.username }}</view>
        </view>
      </view>
    </view>

    <view class="main">
      <view class="card">
        <view class="field-label">用户名</view>
        <view class="control readonly">{{ auth.username }}</view>
        <view class="hint-line">注册后不可修改，用于登录。</view>

        <view class="field-label">生日<text class="optional">（选填）</text></view>
        <picker mode="date" :value="birthday || today" :end="today" @change="onBirthday">
          <view class="control">{{ birthday || '选择生日' }}</view>
        </picker>

        <view class="field-label">身高<text class="optional">（选填）</text></view>
        <input v-model="heightCm" class="control" type="digit" placeholder="例如 165" placeholder-class="ph" />

        <view class="field-label">电话<text class="optional">（选填）</text></view>
        <input v-model="contactPhone" class="control" maxlength="32" placeholder="例如 138****6021" placeholder-class="ph" />
        <view class="hint-line">仅作为个人资料保存，不用于登录，也不会发送验证码。</view>

        <text v-if="error" class="error">{{ error }}</text>
        <button class="btn block save" :disabled="saving" @tap="save">
          {{ saving ? '保存中…' : '保存资料' }}
        </button>
        <view v-if="saved" class="ok">资料已更新</view>
      </view>

      <view class="section">
        <button class="btn ghost block logout" @tap="logout">退出登录</button>
        <view class="note logout-note">退出后账号与健康记录仍保留，重新登录即可查看。</view>
      </view>
    </view>

    <TabBar current="/pages/me/index" />
  </view>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue'
import { onShow } from '@dcloudio/uni-app'
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

const displayName = computed(() => auth.member?.name || auth.username || '她')
const avatarText = computed(() => (auth.username || '她').slice(0, 1).toUpperCase())

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

function onBirthday(event: { detail: { value: string } }) {
  birthday.value = event.detail.value
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
.me-hero {
  padding-bottom: 20px;
}
.profile {
  display: flex;
  align-items: center;
  gap: 14px;
  margin-top: 14px;
}
.avatar {
  width: 64px;
  height: 64px;
  border-radius: 50%;
  background: var(--avatar-grad);
  color: var(--berry-deep);
  font-size: 22px;
  font-weight: 600;
  letter-spacing: 1px;
  display: flex;
  align-items: center;
  justify-content: center;
  border: 2px solid rgba(255, 255, 255, 0.92);
  box-shadow: 0 10px 22px -10px rgba(156, 59, 80, 0.5);
}
.profile-info {
  flex: 1;
  min-width: 0;
}
.name {
  font-size: 18px;
  line-height: 26px;
  font-weight: 600;
  color: var(--ink);
}
.user {
  margin-top: 2px;
  font-size: 13px;
  color: var(--ink-2);
}
.optional {
  color: var(--ink-2);
  font-size: 12px;
}
.save {
  margin-top: 18px;
}
.ok {
  margin-top: 8px;
  font-size: 12px;
  color: var(--berry);
  text-align: center;
}
.section {
  margin-top: 4px;
}
.logout {
  height: 46px;
}
.logout-note {
  margin-top: 10px;
  text-align: center;
}
</style>
