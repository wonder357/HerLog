<template>
  <div class="discussion">
    <header class="card discussion-head">
      <div>
        <p>公开 · 匿名</p>
        <h2>运动讨论区</h2>
        <p>聊聊活动体验、运动习惯和想请教的问题。所有登录用户都可浏览。</p>
      </div>
      <H5Button class="primary" @click="startPost">匿名发帖</H5Button>
    </header>

    <div class="discussion-tools">
      <div class="filters" role="group" aria-label="筛选话题">
        <H5Button class="chip" :aria-pressed="filter === undefined" @click="changeFilter()">全部</H5Button>
        <H5Button v-for="(label, code) in categories" :key="code" class="chip"
          :aria-pressed="filter === code" @click="changeFilter(code)">{{ label }}</H5Button>
      </div>
      <H5Button class="hr-action" :disabled="loading" @click="loadPosts()">刷新</H5Button>
    </div>

    <p v-if="loading && !posts.length" class="card muted" role="status">正在读取讨论…</p>
    <div v-if="feedError" class="card retry" role="alert">
      <span>{{ feedError }}</span><H5Button class="hr-action" @click="loadPosts()">重试</H5Button>
    </div>
    <div v-else-if="!loading && !posts.length" class="card empty">
      <h3>{{ filter ? '这个话题还没有帖子' : '还没有讨论' }}</h3>
      <p class="muted">可以从一次活动体验，或一个想请教的问题开始。</p>
    </div>

    <article v-for="post in posts" :key="post.public_id" class="card discussion-post">
      <div class="post-meta">
        <span class="category">{{ categories[post.category] }}</span>
        <span>{{ post.mine ? '我发布的' : '匿名成员' }} · {{ formatMoment(post.published_at) }}</span>
      </div>
      <h3>{{ post.title }}</h3>
      <p class="post-body">{{ post.body }}</p>
      <p v-if="post.activity" class="attachment"><HerlogIcon name="walk" />打卡项目 · {{ post.activity }}</p>
      <div class="post-actions">
        <H5Button class="hr-action" @click="openThread(post)">{{ post.reply_count ? '回复（' + post.reply_count + '）' : '回复' }}</H5Button>
        <H5Button class="hr-action" @click="chooseAction(post, post.mine ? 'remove' : 'report')">{{ post.mine ? '撤回' : '举报' }}</H5Button>
      </div>
    </article>
    <H5Button v-if="postCursor" class="ghost more" :disabled="loading" @click="loadPosts(true)">{{ loading ? '正在加载…' : '更多讨论' }}</H5Button>

    <HerlogSheet v-if="overlay === 'compose'" title="发起讨论" context="以匿名身份发布，所有登录用户可见" :busy="busy" @close="closeCompose">
      <p class="muted guidelines">请围绕运动体验交流，避免填写体重、体脂数字、联系方式或极端节食方法。</p>
      <div class="filters compose-filters" role="group" aria-label="选择话题">
        <H5Button v-for="(label, code) in categories" :key="code" class="chip"
          :aria-pressed="category === code" :disabled="busy" @click="category = code">{{ label }}</H5Button>
      </div>
      <H5Label class="hr-field-label" for="discussion-title">标题</H5Label>
      <H5Input id="discussion-title" v-model="title" class="field" placeholder="例如，晚饭后散步的感受" maxlength="60" :disabled="busy" />
      <p class="hr-field-label">讨论内容</p>
      <textarea v-model="body" aria-label="讨论内容" class="discussion-textarea post-input" maxlength="600" :disabled="busy" />
      <div v-if="attachment" class="attachment-control">
        <p class="attachment">打卡项目 · {{ attachment.activity }}</p>
        <H5Button class="hr-action" :disabled="busy" @click="attachment = null">移除打卡</H5Button>
      </div>
      <p v-if="actionError" class="error" role="alert">{{ actionError }}</p>
      <template #actions>
        <H5Button class="primary" :disabled="busy || title.trim().length < 2 || !body.trim()" @click="publish">
          {{ busy ? '正在发布…' : '公开发布' }}
        </H5Button>
      </template>
    </HerlogSheet>

    <HerlogSheet v-if="overlay === 'thread' && thread" title="讨论回复" :context="thread.title" :busy="busy" @close="overlay = null">
      <p class="post-body thread-original">{{ thread.body }}</p>
      <p v-if="repliesLoading && !replies.length" class="muted" role="status">正在读取回复…</p>
      <div v-if="replyError" class="retry" role="alert"><span>{{ replyError }}</span><H5Button class="hr-action" @click="loadReplies()">重试</H5Button></div>
      <p v-else-if="!repliesLoading && !replies.length" class="muted">还没有回复，可以聊聊自己的体验。</p>
      <div v-for="reply in replies" :key="reply.public_id" class="reply">
        <div class="reply-meta">
          <span>{{ reply.mine ? '我的回复' : '匿名成员' }} · {{ formatMoment(reply.published_at) }}</span>
          <H5Button class="hr-action" :disabled="busy" @click="chooseAction(thread, reply.mine ? 'remove' : 'report', reply)">
            {{ reply.mine ? '撤回回复' : '举报回复' }}
          </H5Button>
        </div>
        <p class="post-body">{{ reply.body }}</p>
      </div>
      <H5Button v-if="replyCursor" class="hr-action" :disabled="repliesLoading" @click="loadReplies(true)">更多回复</H5Button>
      <p class="hr-field-label">匿名回复</p>
      <textarea v-model="replyBody" aria-label="匿名回复" class="discussion-textarea reply-input" maxlength="300" :disabled="busy" />
      <p v-if="actionError" class="error" role="alert">{{ actionError }}</p>
      <template #actions>
        <H5Button class="primary" :disabled="busy || !replyBody.trim()" @click="publishReply">{{ busy ? '正在发送…' : '公开回复' }}</H5Button>
      </template>
    </HerlogSheet>

    <HerlogSheet v-if="(overlay === 'report' || overlay === 'remove') && target"
      :title="overlay === 'report' ? '举报内容' : target.reply ? '撤回这条回复？' : '撤回这条讨论？'"
      :busy="busy" @close="returnFromAction">
      <template v-if="overlay === 'report'">
        <p class="muted">举报后，这条内容会在你的列表里隐藏。</p>
        <div class="report-options" role="group" aria-label="举报原因">
          <H5Button v-for="(label, code) in reportReasons" :key="code" class="chip" :aria-pressed="reason === code"
            :disabled="busy" @click="reason = code">{{ label }}</H5Button>
        </div>
      </template>
      <p v-else class="muted">{{ target.reply ? '撤回后，其他用户将无法看到这条回复。' : '撤回后，帖子和回复会从讨论区隐藏。' }}</p>
      <p v-if="actionError" class="error" role="alert">{{ actionError }}</p>
      <template #actions>
        <H5Button class="ghost" :disabled="busy" @click="returnFromAction">取消</H5Button>
        <H5Button class="primary" :disabled="busy || (overlay === 'report' && !reason)" @click="confirmAction">
          {{ busy ? '正在处理…' : overlay === 'report' ? '提交举报' : '确认撤回' }}
        </H5Button>
      </template>
    </HerlogSheet>
  </div>
</template>

<script setup lang="ts">
import { onBeforeUnmount, onMounted, ref, watch } from 'vue'
import H5Button from '../../components/H5Button'
import { H5Label } from '../../components/H5Form'
import H5Input from '../../components/H5Input'
import HerlogIcon from '../../components/HerlogIcon.vue'
import HerlogSheet from '../../components/HerlogSheet.vue'
import { ApiRequestError, currentEpoch } from '../../services/httpClient'
import { formatMoment } from '../../shared/dates'
import { newClientKey } from '../../services/weightService'
import { categories, createDiscussion, listDiscussion, listDiscussionReplies, removeDiscussionItem,
  reportDiscussionItem, reportReasons, sendDiscussionReply } from '../../services/exerciseDiscussionService'
import type { DiscussionCategory, DiscussionPost, DiscussionReply, ReportReason } from '../../services/exerciseDiscussionService'
import type { ShareReference } from '../../services/wellnessService'

const props = defineProps<{ reference: ShareReference | null }>()
const emit = defineEmits<{ clearReference: [] }>()
const filter = ref<DiscussionCategory>()
const posts = ref<DiscussionPost[]>([])
const postCursor = ref<number | null>(null)
const loading = ref(false)
const feedError = ref('')
const overlay = ref<'compose' | 'thread' | 'report' | 'remove' | null>(null)
const title = ref('')
const body = ref('')
const category = ref<DiscussionCategory>('experience')
const attachment = ref<ShareReference | null>(null)
const busy = ref(false)
const actionError = ref('')
const thread = ref<DiscussionPost | null>(null)
const replies = ref<DiscussionReply[]>([])
const replyCursor = ref<number | null>(null)
const repliesLoading = ref(false)
const replyError = ref('')
const replyBody = ref('')
const target = ref<{ post: DiscussionPost; reply?: DiscussionReply } | null>(null)
const reason = ref<ReportReason | null>(null)

let postKey = newClientKey()
let replyKey = newClientKey()
let feedRequest = 0
let repliesRequest = 0
const epoch = currentEpoch()
let mounted = true
const active = () => mounted && currentEpoch() === epoch

watch([title, body, category, attachment], () => { postKey = newClientKey() }, { flush: 'sync' })
watch(replyBody, () => { replyKey = newClientKey() }, { flush: 'sync' })
watch(() => props.reference, reference => {
  if (!reference) return
  attachment.value = reference
  category.value = 'checkin'
  startPost()
}, { immediate: true })
onBeforeUnmount(() => { mounted = false })
onMounted(() => { void loadPosts() })

function changeFilter(value?: DiscussionCategory) {
  if (filter.value === value) return
  filter.value = value
  posts.value = []
  postCursor.value = null
  void loadPosts()
}

async function loadPosts(append = false) {
  if (append && (loading.value || !postCursor.value)) return
  const request = ++feedRequest
  const isCurrent = () => active() && request === feedRequest
  loading.value = true
  feedError.value = ''
  try {
    const result = await listDiscussion(filter.value, append ? postCursor.value ?? undefined : undefined)
    if (!isCurrent()) return
    posts.value = append ? [...posts.value, ...result.items] : result.items
    postCursor.value = result.next_cursor
  } catch {
    if (isCurrent()) feedError.value = '讨论列表暂时无法读取。'
  } finally {
    if (isCurrent()) loading.value = false
  }
}

function startPost() {
  actionError.value = ''
  overlay.value = 'compose'
}

function closeCompose() {
  overlay.value = null
  emit('clearReference')
}

async function mutate(operation: () => Promise<void>) {
  if (busy.value || !active()) return
  busy.value = true
  actionError.value = ''
  try {
    await operation()
  } catch (failure) {
    if (active()) actionError.value = failure instanceof ApiRequestError ? failure.message : '操作暂未完成，可以重试。'
  } finally {
    if (active()) busy.value = false
  }
}

function publish() {
  void mutate(async () => {
    const post = await createDiscussion({
      title: title.value.trim(), body: body.value.trim(), category: category.value, client_key: postKey,
      ...(attachment.value?.checkin_id ? { checkin_id: attachment.value.checkin_id } : {})
    })
    if (!active()) return
    title.value = body.value = ''
    category.value = 'experience'
    attachment.value = null
    closeCompose()
    if (filter.value && filter.value !== post.category) changeFilter()
    else void loadPosts()
    uni.showToast({ title: '已公开发布', icon: 'none' })
  })
}

function openThread(post: DiscussionPost) {
  thread.value = post
  replies.value = []
  replyCursor.value = null
  replyBody.value = ''
  actionError.value = ''
  overlay.value = 'thread'
  void loadReplies()
}

async function loadReplies(append = false) {
  const post = thread.value
  if (!post || (append && (repliesLoading.value || !replyCursor.value))) return
  const request = ++repliesRequest
  const isCurrent = () => active() && request === repliesRequest
  repliesLoading.value = true
  replyError.value = ''
  try {
    const result = await listDiscussionReplies(post.public_id, append ? replyCursor.value ?? undefined : undefined)
    if (!isCurrent()) return
    replies.value = append ? [...replies.value, ...result.items] : result.items
    replyCursor.value = result.next_cursor
  } catch (failure) {
    if (isCurrent()) replyError.value = failure instanceof ApiRequestError && failure.status === 404
      ? '这条讨论已不可见。' : '暂时无法读取回复。'
  } finally {
    if (isCurrent()) repliesLoading.value = false
  }
}

function publishReply() {
  const id = thread.value?.public_id
  if (!id) return
  void mutate(async () => {
    await sendDiscussionReply(id, replyBody.value.trim(), replyKey)
    if (!active()) return
    replyBody.value = ''
    void loadReplies()
    void loadPosts()
  })
}

function chooseAction(post: DiscussionPost, action: 'report' | 'remove', reply?: DiscussionReply) {
  target.value = { post, reply }
  actionError.value = ''
  reason.value = null
  overlay.value = action
}

function returnFromAction() {
  overlay.value = target.value?.reply ? 'thread' : null
  target.value = null
  actionError.value = ''
}

function confirmAction() {
  const item = target.value
  const reporting = overlay.value === 'report'
  const selectedReason = reason.value
  if (!item || (reporting && !selectedReason)) return
  void mutate(async () => {
    if (reporting && selectedReason) await reportDiscussionItem(item.post.public_id, selectedReason, item.reply?.public_id)
    else await removeDiscussionItem(item.post.public_id, item.reply?.public_id)
    if (!active()) return
    if (item.reply) {
      replies.value = replies.value.filter(reply => reply.public_id !== item.reply?.public_id)
      void loadReplies()
    } else posts.value = posts.value.filter(post => post.public_id !== item.post.public_id)
    returnFromAction()
    void loadPosts()
    uni.showToast({ title: reporting ? '已举报并隐藏' : '已撤回', icon: 'none' })
  })
}
</script>

<style scoped>
.discussion { min-width:0; }
.discussion-head { display:grid; grid-template-columns:minmax(0,1fr) auto; align-items:end; gap:10px; padding:15px 12px; background:linear-gradient(135deg,var(--hr-rose-soft),var(--hr-peach)); }
.discussion-head h2 { margin:3px 0 5px; font-size:21px; }
.discussion-head p { margin:0; color:var(--hr-ink-2); font-size:13px; }
.discussion-head p:first-child { color:var(--hr-rose-deep); font-weight:650; }
.discussion-head .primary { white-space:nowrap; min-height:44px; width:auto; padding:6px 12px; font-size:13px; }
.discussion-tools { display:flex; flex-wrap:wrap; align-items:center; justify-content:space-between; gap:2px; margin-bottom:8px; }
.filters { display:flex; flex-wrap:wrap; gap:6px; }
.chip { min-height:44px; border:1px solid var(--hr-line-strong); border-radius:14px; background:var(--hr-surface); color:var(--hr-ink-2); padding:5px 9px; font-size:13px; }
.chip[aria-pressed='true'] { border-color:var(--hr-rose); background:var(--hr-rose-soft); color:var(--hr-rose-deep); font-weight:650; }
.discussion-tools .hr-action { padding-inline:3px; font-size:13px; }
.discussion-post { padding:13px 14px 5px; }
.post-meta,.reply-meta { display:flex; align-items:center; flex-wrap:wrap; gap:5px 8px; color:var(--hr-ink-2); font-size:12px; }
.category { padding:2px 7px; border-radius:8px; background:var(--hr-paper-deep); color:var(--hr-ink); }
.discussion-post h3,.empty h3 { margin:8px 0 4px; font-size:16px; line-height:1.45; overflow-wrap:anywhere; }
.post-body { white-space:pre-wrap; overflow-wrap:anywhere; line-height:1.65; margin:0; color:var(--hr-ink); font-size:14px; }
.discussion-post .post-body { display:-webkit-box; -webkit-box-orient:vertical; -webkit-line-clamp:4; overflow:hidden; }
.thread-original { margin:4px 0 12px; padding:10px; border-radius:12px; background:var(--hr-paper-deep); }
.post-actions,.reply-meta { display:flex; justify-content:space-between; }
.post-actions { margin-top:6px; border-top:1px solid var(--hr-line); }
.post-actions .hr-action,.reply-meta .hr-action { padding-inline:2px; font-size:13px; }
.attachment { display:flex; align-items:center; gap:5px; margin:8px 0 0; color:var(--hr-ink-2); font-size:13px; }
.attachment svg { width:16px; height:16px; }
.attachment-control,.retry { display:flex; gap:8px; align-items:center; justify-content:space-between; }
.empty h3,.empty p,.guidelines { margin:0 0 4px; }
.compose-filters,.report-options { margin:9px 0 14px; }
.report-options { display:flex; flex-wrap:wrap; gap:7px; }
.discussion-textarea { box-sizing:border-box; width:100%; min-height:100px; padding:9px 10px; border:1px solid var(--hr-line-strong); border-radius:12px; background:var(--hr-surface); font:16px/1.5 var(--hr-font); color:var(--hr-ink); }
.discussion-textarea:focus-within { border-color:var(--hr-rose); }
.reply { padding:2px 0 9px; margin-bottom:8px; border-bottom:1px solid var(--hr-line); }
.more { margin-bottom:12px; }
</style>
