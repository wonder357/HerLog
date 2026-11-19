<template>
  <view class="wellness-group">
    <view class="group-head">
      <text class="group-title">{{ topic === 'skin' ? '护理交流' : '运动同行' }}</text>
      <text class="group-muted">邀请制 · 仅组内可见</text>
    </view>
    <view v-if="error" class="group-error" role="alert">{{ error }}</view>
    <view v-if="loading" class="group-muted" role="status">正在读取小组…</view>
    <view v-else-if="!groups.length" class="group-muted">
      暂时没有读取到小组。<H5Button class="group-text" @click="refresh">重试</H5Button>
    </view>
    <template v-else>
      <view class="group-options">
        <H5Button v-for="item in groups" :key="item.group_key" class="group-chip"
          :class="{ selected: key === item.group_key }" :disabled="busy" @click="setGroup(item.group_key)">
          {{ item.title }}
        </H5Button>
      </view>
      <view v-if="!current?.joined" class="group-panel">
        <view class="group-muted">
          {{ key === 'general' ? '用匿名卡片交流日常记录。接受邀请后才可浏览和发布。' : '此小组按周期阶段匹配，组员可能由分组推测你的阶段。你也可以选择通用小组。' }}
        </view>
        <input v-model="inviteCode" class="group-input" aria-label="邀请码" placeholder="输入小组邀请码" maxlength="64" />
        <H5Button class="group-primary" :disabled="busy || !inviteCode.trim()" @click="confirmJoin">同意并加入</H5Button>
      </view>

      <template v-else>
        <view v-if="reference" class="group-panel">
          <view class="group-title small">发布预览</view>
          <view class="group-muted">仅 {{ current.title }} 成员可见</view>
          <view class="group-options">
            <H5Button v-for="item in availableCaptions" :key="item.code" class="group-chip"
              :class="{ selected: caption === item.code }" :disabled="busy" @click="selectCaption(item.code)">
              {{ item.label }}
            </H5Button>
          </view>
          <view class="preview">
            <view class="group-muted">匿名成员</view>
            <view v-if="reference.activity">{{ reference.activity }}</view>
            <view>{{ availableCaptions.find(item => item.code === caption)?.label }}</view>
            <view v-if="includeDuration && reference.duration" class="group-muted">{{ durationLabel }}</view>
          </view>
          <H5Button v-if="reference.duration" class="group-chip" :class="{ selected: includeDuration }"
            :disabled="busy" @click="toggleDuration">
            {{ includeDuration ? '已包含时长区间' : '包含时长区间' }}
          </H5Button>
          <H5Button class="group-primary" :disabled="busy" @click="publish">{{ busy ? '正在处理…' : '确认发布' }}</H5Button>
        </view>
        <view v-else class="group-muted group-panel">
          {{ topic === 'skin' ? '保存一条护理日记后，即可从日记发起分享。' : '保存一次运动或休息后，即可从打卡发起分享。' }}
        </view>

        <view v-if="feedError" class="group-muted">
          动态没有加载成功。<H5Button class="group-text" @click="loadFeed(false)">重试</H5Button>
        </view>
        <view v-else-if="!feed.length" class="group-muted group-panel">这里还没有分享。</view>
        <view v-for="item in feed" :key="item.public_id" class="group-post">
          <view class="group-post-heading">
            <text>{{ item.mine ? '我的匿名分享' : item.display_name }}</text>
            <H5Button v-if="item.mine" class="group-text" @click="withdraw(item.public_id)">撤回</H5Button>
            <H5Button v-else class="group-text" @click="chooseReport(item.public_id)">举报</H5Button>
          </view>
          <view>{{ item.snapshot.activity }} {{ item.snapshot.caption }}</view>
          <view v-if="item.snapshot.duration_bucket" class="group-muted">{{ item.snapshot.duration_bucket }}</view>
          <template v-if="topic === 'skin'">
            <view v-for="reply in item.replies" :key="reply.text" class="group-muted">{{ reply.text }} · {{ reply.count }} 人</view>
            <H5Button v-if="!item.mine" class="group-text" :disabled="busy" @click="chooseReply(item.public_id)">回应</H5Button>
          </template>
        </view>
        <H5Button v-if="cursor" class="group-chip" :disabled="fetching" @click="loadFeed(true)">更多动态</H5Button>
        <H5Button class="group-text" :disabled="busy" @click="confirmLeave">退出小组</H5Button>
      </template>
    </template>
    <view v-if="mine.length" class="group-panel">
      <view class="group-title small">我的发布</view>
      <view v-for="item in mine" :key="item.public_id" class="group-mine">
        <text>{{ item.snapshot.caption }}</text>
        <text class="group-muted">{{ ({ published: '可见', withdrawn: '已撤回', hidden: '已隐藏' })[item.status] }}</text>
      </view>
    </view>
  </view>
</template>

<script setup lang="ts">
import H5Button from './H5Button'
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { ApiRequestError, currentEpoch } from '../services/httpClient'
import { newClientKey } from '../services/weightService'
import { captions, joinGroup, leaveGroup, listGroups, listShares, ownShares, postShare, replyToSkinShare, reportShare, withdrawShare } from '../services/wellnessService'
import type { Group, Share, ShareReference, Topic } from '../services/wellnessService'

const props = defineProps<{ topic: Topic; reference?: ShareReference | null }>()
const emit = defineEmits<{ published: [] }>()
const groups = ref<Group[]>([])
const key = ref('general')
const current = computed(() => groups.value.find(item => item.group_key === key.value))
const inviteCode = ref('')
const availableCaptions = computed(() => props.reference?.activity === '休息'
  ? captions.exercise.filter(item => item.code !== 'checked_in')
  : captions[props.topic])
const caption = ref<string>(availableCaptions.value[0].code)
const includeDuration = ref(false)
const durationLabel = computed(() => {
  const minutes = props.reference?.duration ?? 0
  return minutes < 10 ? '十分钟以内' : minutes < 30 ? '十至二十九分钟' : '三十分钟或以上'
})
const feed = ref<Share[]>([])
const mine = ref<Share[]>([])
const cursor = ref<number | null>(null)
const error = ref('')
const feedError = ref(false)
const loading = ref(false)
const fetching = ref(false)
const busy = ref(false)
let active = true
let feedVersion = 0
let shareKey = newClientKey()

watch(() => props.reference, () => {
  shareKey = newClientKey()
  includeDuration.value = false
  caption.value = availableCaptions.value[0].code
})
onBeforeUnmount(() => { active = false })
onMounted(refresh)

function selectCaption(value: string) {
  if (caption.value !== value) shareKey = newClientKey()
  caption.value = value
}
function toggleDuration() {
  shareKey = newClientKey()
  includeDuration.value = !includeDuration.value
}
function setGroup(value: string) {
  if (value === key.value) return
  key.value = value
  inviteCode.value = ''
  shareKey = newClientKey()
  void loadFeed(false)
}

async function refresh() {
  const epoch = currentEpoch()
  loading.value = true
  error.value = ''
  try {
    const [items, personal] = await Promise.all([listGroups(props.topic), ownShares(props.topic)])
    if (!active || epoch !== currentEpoch()) return
    groups.value = items
    mine.value = personal
    if (!items.some(item => item.group_key === key.value)) key.value = items[0]?.group_key ?? 'general'
    await loadFeed(false)
  } catch {
    if (active && epoch === currentEpoch()) error.value = '小组没有加载成功'
  } finally {
    loading.value = false
  }
}

async function loadFeed(append: boolean) {
  const version = ++feedVersion
  const epoch = currentEpoch()
  const group = current.value
  feedError.value = false
  if (!append) {
    feed.value = []
    cursor.value = null
  }
  if (!group?.joined) {
    fetching.value = false
    return
  }
  fetching.value = true
  try {
    const result = await listShares(props.topic, group.group_key, append ? cursor.value ?? undefined : undefined)
    if (!active || epoch !== currentEpoch() || version !== feedVersion) return
    feed.value = append ? [...feed.value, ...result.items] : result.items
    cursor.value = result.next_cursor
  } catch {
    if (active && epoch === currentEpoch() && version === feedVersion) feedError.value = true
  } finally {
    if (version === feedVersion) fetching.value = false
  }
}

async function change(action: () => Promise<unknown>) {
  if (busy.value) return
  const epoch = currentEpoch()
  busy.value = true
  error.value = ''
  try {
    await action()
    if (active && epoch === currentEpoch()) await refresh()
  } catch (failure) {
    if (active && epoch === currentEpoch()) error.value =
      failure instanceof ApiRequestError ? failure.message : '操作没有完成，可以重试'
  } finally {
    busy.value = false
  }
}

function confirmJoin() {
  const invite = inviteCode.value.trim()
  const groupKey = key.value
  uni.showModal({
    title: '加入匿名小组',
    content: '加入后可阅读该组的卡片。发布前会再次向你确认内容和可见范围。',
    success: result => {
      if (result.confirm) void change(() => joinGroup(props.topic, groupKey, invite))
    }
  })
}

function confirmLeave() {
  const groupKey = key.value
  uni.showModal({
    title: '退出小组',
    content: '退出后，本组内你已发布的卡片会撤回，个人记录仍可在自己的日记查看。',
    success: result => {
      if (result.confirm) void change(() => leaveGroup(props.topic, groupKey))
    }
  })
}

async function publish() {
  const reference = props.reference
  if (!reference || !current.value?.joined) return
  await change(async () => {
    const share = await postShare(props.topic, key.value, reference, caption.value, includeDuration.value, shareKey)
    if (active && share.status === 'published') {
      emit('published')
      uni.showToast({ title: '已发布到小组', icon: 'none' })
    }
  })
}

function withdraw(id: string) {
  uni.showModal({
    title: '撤回这张卡片？',
    content: '小组成员将无法再查看这张卡片。',
    success: result => {
      if (result.confirm) void change(() => withdrawShare(props.topic, id))
    }
  })
}

function chooseReport(id: string) {
  const labels = ['身体比较', '身材羞辱', '极端节食', '个人信息', '其他原因']
  const reasons = ['comparison', 'body_shaming', 'restriction', 'personal_info', 'other']
  uni.showActionSheet({
    itemList: labels,
    success: ({ tapIndex }) => {
      const reason = reasons[tapIndex]
      if (reason) void change(() => reportShare(props.topic, id, reason))
    }
  })
}

function chooseReply(id: string) {
  const labels = ['我也在记护理日记', '谢谢分享', '可以留意自己接下来的感受']
  const codes = ['also_record', 'thanks', 'keep_observing']
  uni.showActionSheet({
    itemList: labels,
    success: ({ tapIndex }) => {
      const code = codes[tapIndex]
      if (code) void change(() => replyToSkinShare(id, code))
    }
  })
}
</script>

<style scoped>
.wellness-group { display: grid; gap: 12px; color: var(--hr-ink); line-height: 1.55; }
.group-head,.group-post-heading,.group-mine { display: flex; gap: 8px; justify-content: space-between; align-items: center; flex-wrap: wrap; }
.group-title { font-size: 19px; font-weight: 680; }
.group-title.small { font-size: 16px; }
.group-muted { font-size: 13px; color: var(--hr-ink-2); }
.group-panel,.group-post { padding: 14px; border-radius: var(--hr-radius); background: var(--hr-surface); border: 1px solid var(--hr-line); }
.group-options { display: flex; flex-wrap: wrap; gap: 8px; margin: 8px 0; }
.group-input { margin: 12px 0; height: 46px; padding: 0 12px; border: 1px solid var(--hr-line-strong); border-radius: 11px; background: #fff; }
.group-chip,.group-primary,.group-text { margin: 0; font-size: 13px; min-height: 44px; line-height: 1.3; padding: 8px 11px; }
.group-chip { border: 1px solid var(--hr-line); border-radius: 999px; background: var(--hr-surface); color: var(--hr-ink-2); }
.group-chip.selected { background: var(--hr-rose-soft); color: var(--hr-rose-deep); border-color: var(--hr-rose); }
.group-primary { border: 0; margin-top: 10px; width: 100%; border-radius: 999px; background: var(--hr-rose); color: #fff; }
.group-text { border: 0; background: transparent; color: var(--hr-rose-deep); border-radius: 10px; }
.preview { padding: 12px; border-left: 2px solid var(--hr-rose); background: var(--hr-paper); margin: 8px 0; border-radius: 0 10px 10px 0; }
.group-error { padding: 10px; background: var(--hr-danger-soft); color: var(--hr-danger); border-radius: 12px; }
.group-mine { padding: 8px 0; border-bottom: 1px solid var(--hr-line); }
</style>
