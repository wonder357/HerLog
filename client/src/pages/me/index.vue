<template>
  <view class="page">
    <view class="card">
      <view class="row">
        <view class="label">用户名</view>
        <view class="readonly">{{ auth.username }}</view>
      </view>
      <view class="muted">用户名来自注册时的会员身份，第一版不支持修改。</view>
    </view>

    <view class="card">
      <view class="row">
        <view class="label">生日</view>
        <picker mode="date" :value="birthday || today" :end="today" @change="onBirthday">
          <view class="value">{{ birthday || '选填' }}</view>
        </picker>
      </view>
      <view class="row">
        <view class="label">身高</view>
        <input v-model="heightCm" class="value input" type="digit" placeholder="选填，单位 cm" />
      </view>
      <view class="row">
        <view class="label">电话</view>
        <input v-model="contactPhone" class="value input" maxlength="32" placeholder="选填，仅作资料" />
      </view>
      <text v-if="error" class="error">{{ error }}</text>
      <button class="primary" :disabled="saving" @tap="save">
        {{ saving ? '保存中…' : '保存资料' }}
      </button>
      <view v-if="saved" class="ok">资料已更新</view>
    </view>

    <view class="card">
      <view class="ghost" @tap="logout">退出登录</view>
      <view class="muted logout-note">退出后本机不再保留登录会话，重新登录仍可回看该账号的记录。</view>
    </view>

    <TabBar current="/pages/me/index" />
  </view>
</template>

<script setup lang="ts">
import { ref } from 'vue'
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
.page {
  min-height: 100vh;
  padding: 12px 16px 76px;
  box-sizing: border-box;
}
.row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  min-height: 44px;
  border-bottom: 1px solid #f4ebe7;
}
.label {
  font-size: 14px;
  color: #4b413d;
}
.readonly {
  color: #8a7f7a;
  font-size: 14px;
}
.value {
  font-size: 14px;
  color: #4b413d;
  text-align: right;
}
.input {
  width: 60%;
  height: 40px;
}
.primary {
  margin-top: 14px;
}
.ok {
  margin-top: 8px;
  font-size: 12px;
  color: #3f7d52;
}
.logout-note {
  margin-top: 8px;
  line-height: 1.6;
}
</style>
