<template>
  <div class="discussion">
    <header class="card discussion-head">
      <div>
        <h2>运动讨论区</h2>
        <p>匿名聊动作、运动习惯与周期体验。登录用户可见。</p>
      </div>
      <H5Button class="primary" @click="startPost"><HerlogIcon name="chat" />发帖</H5Button>
    </header>

    <section class="card discussion-tools" aria-label="查找讨论">
      <div class="feed-views" role="group" aria-label="讨论列表">
        <H5Button v-for="(label, code) in views" :key="code" class="feed-view" :aria-pressed="view === code"
          @click="changeView(code)">{{ label }}</H5Button>
      </div>
      <H5Form class="discussion-search" role="search" @submit.prevent="search">
        <H5Input v-model="searchInput" type="search" aria-label="搜索运动讨论" class="field" placeholder="搜索标题或内容" maxlength="60" />
        <H5Button type="submit" class="ghost">搜索</H5Button>
        <H5Button v-if="keyword" class="hr-action" @click="clearSearch">清除</H5Button>
      </H5Form>
      <div class="filters" role="group" aria-label="筛选话题">
        <H5Button class="chip" :aria-pressed="filter === undefined" @click="changeFilter()">全部</H5Button>
        <H5Button v-for="(label, code) in categories" :key="code" class="chip"
          :aria-pressed="filter === code" @click="changeFilter(code)">{{ label }}</H5Button>
      </div>
      <div class="feed-sort">
        <div v-if="view === 'all'" role="group" aria-label="排序方式">
          <H5Button v-for="(label, code) in orders" :key="code" class="hr-action feed-order" :aria-pressed="sort === code"
            @click="changeSort(code)">{{ label }}</H5Button>
        </div>
        <H5Button class="hr-action" :disabled="loading" @click="loadPosts()">刷新</H5Button>
      </div>
    </section>

    <p v-if="loading && !posts.length" class="card muted" role="status">正在读取讨论…</p>
    <div v-if="feedError" class="card retry" role="alert">
      <span>{{ feedError }}</span><H5Button class="hr-action" @click="loadPosts(retryAppend)">重试</H5Button>
    </div>
    <div v-else-if="!loading && !posts.length" class="card empty">
      <h3>{{ emptyState.title }}</h3>
      <p class="muted">{{ emptyState.note }}</p>
    </div>

    <article v-for="post in posts" :key="post.public_id" class="card discussion-post">
      <div class="post-meta">
        <span>{{ post.mine ? '我发布的' : '匿名成员' }} · {{ formatMoment(post.published_at) }}</span>
        <span class="category">{{ categories[post.category] }}</span>
      </div>
      <h3><H5Button class="open-post" @click="openThread(post)">{{ post.title }}</H5Button></h3>
      <p class="post-body">{{ post.body }}</p>
      <p v-if="post.activity" class="attachment"><HerlogIcon name="walk" />打卡项目 · {{ post.activity }}</p>
      <div class="post-actions">
        <H5Button class="hr-action" :aria-pressed="post.liked" :disabled="reactionBusy.has(post.public_id)"
          @click="react(post, 'like')">{{ post.liked ? '已点赞' : '点赞' }}<span v-if="post.like_count">{{ post.like_count }}</span></H5Button>
        <H5Button class="hr-action" @click="openThread(post)">回复<span v-if="post.reply_count">{{ post.reply_count }}</span></H5Button>
        <H5Button class="hr-action" :aria-pressed="post.saved" :disabled="reactionBusy.has(post.public_id)"
          @click="react(post, 'save')">{{ post.saved ? '已收藏' : '收藏' }}</H5Button>
        <H5Button class="hr-action" @click="managePost(post)">更多</H5Button>
      </div>
    </article>
    <H5Button v-if="postCursor" class="ghost more" :disabled="loading" @click="loadPosts(true)">{{ loading ? '正在加载…' : '更多讨论' }}</H5Button>

    <HerlogSheet v-if="overlay === 'compose'" :title="editing ? '编辑讨论' : '发起讨论'"
      context="以匿名身份发布，所有登录用户可见" :busy="busy" @close="closeCompose">
      <p class="muted guidelines">请围绕运动体验交流。体重或体脂比较、身材评价、极端节食方法与联系方式禁止发布。</p>
      <div class="filters compose-filters" role="group" aria-label="选择话题">
        <H5Button v-for="(label, code) in categories" :key="code" class="chip"
          :aria-pressed="category === code" :disabled="busy" @click="category = code">{{ label }}</H5Button>
      </div>
      <H5Label class="hr-field-label" for="discussion-title">标题</H5Label>
      <H5Input id="discussion-title" v-model="title" class="field" placeholder="例如，晚饭后散步的感受" maxlength="60" :disabled="busy" />
      <H5Label for="discussion-body" class="hr-field-label">讨论内容</H5Label>
      <component :is="'textarea'" id="discussion-body" :value="body" class="discussion-textarea"
        maxlength="600" :disabled="busy" @input="body = ($event.target as HTMLTextAreaElement).value" />
      <p class="text-limit">{{ body.length }}/600</p>
      <div v-if="attachment" class="attachment-control">
        <p class="attachment">打卡项目 · {{ attachment.activity }}</p>
        <H5Button class="hr-action" :disabled="busy" @click="attachment = null">移除打卡</H5Button>
      </div>
      <p v-if="editing?.activity" class="attachment">已公开的打卡项目 · {{ editing.activity }}</p>
      <p v-if="actionError" class="error" role="alert">{{ actionError }}</p>
      <template #actions>
        <H5Button class="primary" :disabled="busy || title.trim().length < 2 || !body.trim()" @click="publish">
          {{ busy ? '正在保存…' : editing ? '保存修改' : '公开发布' }}
        </H5Button>
      </template>
    </HerlogSheet>

    <HerlogSheet v-if="overlay === 'thread' && thread" title="讨论回复" :context="threadUnavailable ? '' : thread.title" :busy="busy" @close="overlay = null">
      <p v-if="!threadUnavailable" class="post-body thread-original">{{ thread.body }}</p>
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
      <template v-if="!threadUnavailable">
        <H5Label for="discussion-reply" class="hr-field-label">匿名回复</H5Label>
        <component :is="'textarea'" id="discussion-reply" :value="replyBody" class="discussion-textarea"
          maxlength="300" :disabled="busy" @input="replyBody = ($event.target as HTMLTextAreaElement).value" />
      </template>
      <p v-if="actionError" class="error" role="alert">{{ actionError }}</p>
      <template #actions>
        <H5Button v-if="!threadUnavailable" class="primary" :disabled="busy || repliesLoading || !replyBody.trim()" @click="publishReply">{{ busy ? '正在发送…' : '公开回复' }}</H5Button>
      </template>
    </HerlogSheet>

    <HerlogSheet v-if="overlay === 'manage' && target" :title="target.post.title" @close="returnFromAction">
      <div class="post-menu">
        <H5Button v-if="target.post.mine" class="ghost" @click="startEdit(target.post)">编辑讨论</H5Button>
        <H5Button class="ghost" @click="chooseAction(target.post, target.post.mine ? 'remove' : 'report')">
          {{ target.post.mine ? '撤回讨论' : '举报讨论' }}
        </H5Button>
      </div>
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
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import H5Button from '../../components/H5Button'
import H5Form, { H5Label } from '../../components/H5Form'
import H5Input from '../../components/H5Input'
import HerlogIcon from '../../components/HerlogIcon.vue'
import HerlogSheet from '../../components/HerlogSheet.vue'
import { ApiRequestError, currentEpoch } from '../../services/httpClient'
import { formatMoment } from '../../shared/dates'
import { newClientKey } from '../../services/weightService'
import { categories, createDiscussion, editDiscussion, listDiscussion, listDiscussionReplies, removeDiscussionItem,
  reportDiscussionItem, reportReasons, sendDiscussionReply, setDiscussionReaction } from '../../services/exerciseDiscussionService'
import type { DiscussionCategory, DiscussionPost, DiscussionReply, DiscussionSort, DiscussionView, ReactionKind, ReportReason } from '../../services/exerciseDiscussionService'
import type { ShareReference } from '../../services/wellnessService'

const props = defineProps<{ reference: ShareReference | null }>()
const emit = defineEmits<{ clearReference: [] }>()
const views = { all: '讨论', saved: '我的收藏', mine: '我的帖子' } as const
const orders = { latest: '最新', popular: '热门' } as const
const view = ref<DiscussionView>('all')
const sort = ref<DiscussionSort>('latest')
const filter = ref<DiscussionCategory>()
const searchInput = ref('')
const keyword = ref('')
const posts = ref<DiscussionPost[]>([])
const postCursor = ref<{ id: number; likes?: number } | null>(null)
const loading = ref(false)
const feedError = ref('')
const retryAppend = ref(false)
const reactionBusy = ref(new Set<string>())
const overlay = ref<'compose' | 'thread' | 'manage' | 'report' | 'remove' | null>(null)
const editing = ref<DiscussionPost | null>(null)
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
const threadUnavailable = ref(false)
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
const emptyState = computed(() => {
  if (keyword.value || filter.value) return { title: '没有符合条件的帖子', note: '试试其他关键词或话题。' }
  if (view.value === 'saved') return { title: '还没有收藏', note: '收藏的讨论会保存在这里。' }
  if (view.value === 'mine') return { title: '你还没有发布讨论', note: '发帖后，可以在这里编辑或撤回。' }
  return { title: '还没有讨论', note: '可以从一次活动体验，或一个想请教的问题开始。' }
})

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
  resetFeed()
}

function changeView(value: DiscussionView) {
  if (view.value === value) return
  view.value = value
  filter.value = undefined
  keyword.value = searchInput.value = ''
  resetFeed()
}

function changeSort(value: DiscussionSort) {
  if (sort.value === value) return
  sort.value = value
  resetFeed()
}

function search() {
  keyword.value = searchInput.value.trim()
  resetFeed()
}

function clearSearch() {
  searchInput.value = ''
  search()
}

function resetFeed() {
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
  retryAppend.value = append
  try {
    const cursor = append ? postCursor.value : null
    const result = await listDiscussion({
      view: view.value, sort: view.value === 'all' ? sort.value : 'latest',
      ...(filter.value ? { category: filter.value } : {}),
      ...(keyword.value ? { q: keyword.value } : {}),
      ...(cursor ? { cursor: cursor.id } : {}),
      ...(cursor?.likes !== undefined ? { cursor_likes: cursor.likes } : {})
    })
    if (!isCurrent()) return
    const existing = new Set(append ? posts.value.map(post => post.public_id) : [])
    posts.value = append ? [...posts.value, ...result.items.filter(post => !existing.has(post.public_id))] : result.items
    postCursor.value = result.next_cursor === null ? null : {
      id: result.next_cursor, likes: result.next_cursor_likes ?? undefined
    }
  } catch {
    if (isCurrent()) feedError.value = '讨论列表暂时无法读取。'
  } finally {
    if (isCurrent()) loading.value = false
  }
}

function startPost() {
  editing.value = null
  actionError.value = ''
  overlay.value = 'compose'
}

function closeCompose() {
  overlay.value = null
  editing.value = null
  title.value = body.value = ''
  category.value = 'experience'
  attachment.value = null
  postKey = newClientKey()
  emit('clearReference')
}

function startEdit(post: DiscussionPost) {
  editing.value = post
  title.value = post.title
  body.value = post.body
  category.value = post.category
  attachment.value = null
  actionError.value = ''
  target.value = null
  overlay.value = 'compose'
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
    const text = { title: title.value.trim(), body: body.value.trim(), category: category.value }
    const original = editing.value
    if (original) await editDiscussion(original.public_id, text)
    else await createDiscussion({
      ...text, client_key: postKey, ...(attachment.value?.checkin_id ? { checkin_id: attachment.value.checkin_id } : {})
    })
    if (!active()) return
    closeCompose()
    if (!original && view.value !== 'mine') changeView('mine')
    else void loadPosts()
    uni.showToast({ title: original ? '已保存修改' : '已公开发布', icon: 'none' })
  })
}

async function react(post: DiscussionPost, kind: ReactionKind) {
  const id = post.public_id
  if (!active() || reactionBusy.value.has(id)) return
  const enabled = !(kind === 'like' ? post.liked : post.saved)
  reactionBusy.value.add(id)
  try {
    const state = await setDiscussionReaction(id, kind, enabled)
    if (!active()) return
    if (view.value === 'saved' && !state.saved) {
      posts.value = posts.value.filter(item => item.public_id !== id)
      void loadPosts()
    } else if (loading.value) {
      void loadPosts()
    } else {
      posts.value = posts.value.map(item => item.public_id === id ? { ...item, ...state } : item)
    }
  } catch (failure) {
    if (!active()) return
    if (failure instanceof ApiRequestError && failure.status === 404) {
      posts.value = posts.value.filter(item => item.public_id !== id)
      uni.showToast({ title: '这条讨论已不可见', icon: 'none' })
    } else {
      uni.showToast({ title: '操作暂未完成，可以重试', icon: 'none' })
    }
  } finally {
    reactionBusy.value.delete(id)
  }
}

function openThread(post: DiscussionPost) {
  thread.value = post
  replies.value = []
  replyCursor.value = null
  replyBody.value = ''
  actionError.value = ''
  threadUnavailable.value = false
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
    if (!isCurrent()) return
    threadUnavailable.value = failure instanceof ApiRequestError && failure.status === 404
    replyError.value = threadUnavailable.value ? '这条讨论已不可见。' : '暂时无法读取回复。'
    if (threadUnavailable.value) {
      replies.value = []
      replyCursor.value = null
      posts.value = posts.value.filter(item => item.public_id !== post.public_id)
    }
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

function managePost(post: DiscussionPost) {
  target.value = { post }
  overlay.value = 'manage'
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
.discussion-head { display:grid; grid-template-columns:minmax(0,1fr) auto; align-items:center; gap:12px; padding:16px; background:linear-gradient(132deg,var(--hr-peach),var(--hr-rose-soft)); }
.discussion-head h2 { margin:0 0 4px; font:700 23px/1.25 var(--hr-serif); }
.discussion-head p { margin:0; color:var(--hr-ink-2); font-size:13px; line-height:1.5; }
.discussion-head .primary { display:inline-flex; align-items:center; gap:5px; white-space:nowrap; min-height:44px; width:auto; padding:6px 12px; font-size:14px; }
.discussion-head svg { width:17px; height:17px; }
.discussion-tools { display:grid; gap:9px; padding:8px 12px 2px; }
.feed-views { display:grid; grid-template-columns:repeat(3,minmax(0,1fr)); border-bottom:1px solid var(--hr-line); }
.feed-view { min-height:44px; padding:4px; color:var(--hr-ink-2); background:transparent; border:0; border-bottom:2px solid transparent; font:600 14px var(--hr-font); }
.feed-view[aria-pressed='true'] { border-color:var(--hr-rose-deep); color:var(--hr-rose-deep); }
.discussion-search { display:flex; align-items:center; gap:6px; }
.discussion-search .field { flex:1; width:0; min-width:0; min-height:44px; }
.discussion-search .ghost { width:auto; padding:6px 10px; font-size:13px; }
.feed-sort { display:flex; align-items:center; justify-content:space-between; gap:8px; min-width:0; }
.feed-sort div { display:flex; gap:12px; }
.filters { display:flex; flex-wrap:wrap; gap:6px; }
.chip { min-height:44px; border:1px solid var(--hr-line-strong); border-radius:12px; background:var(--hr-surface); color:var(--hr-ink-2); padding:5px 8px; font-size:13px; }
.chip[aria-pressed='true'] { border-color:var(--hr-rose); background:var(--hr-rose-soft); color:var(--hr-rose-deep); font-weight:650; }
.discussion-tools .hr-action { padding-inline:4px; font-size:13px; }
.feed-order[aria-pressed='true'] { color:var(--hr-rose-deep); font-weight:700; text-decoration:underline; text-underline-offset:4px; }
.discussion-post { padding:13px 14px 4px; }
.post-meta,.reply-meta { display:flex; align-items:center; flex-wrap:wrap; gap:5px 8px; color:var(--hr-ink-2); font-size:12px; }
.post-meta { justify-content:space-between; }
.category { padding:2px 7px; border-radius:6px; background:var(--hr-plum-soft); color:var(--hr-plum); }
.discussion-post h3,.empty h3 { margin:3px 0 0; font-size:17px; line-height:1.45; overflow-wrap:anywhere; }
.open-post { display:block; width:100%; min-height:44px; padding:5px 0; text-align:left; border:0; background:transparent; color:var(--hr-ink); font:inherit; overflow-wrap:anywhere; }
.post-body { white-space:pre-wrap; overflow-wrap:anywhere; line-height:1.65; margin:0; color:var(--hr-ink); font-size:14px; }
.discussion-post .post-body { display:-webkit-box; -webkit-box-orient:vertical; -webkit-line-clamp:4; overflow:hidden; }
.thread-original { margin:4px 0 12px; padding:10px; border-radius:12px; background:var(--hr-paper-deep); }
.post-actions { display:grid; grid-template-columns:repeat(4,minmax(0,1fr)); margin-top:9px; border-top:1px solid var(--hr-line); }
.post-actions .hr-action,.reply-meta .hr-action { padding-inline:1px; font-size:13px; }
.post-actions .hr-action span { padding-inline-start:4px; font-variant-numeric:tabular-nums; }
.post-actions .hr-action[aria-pressed='true'] { color:var(--hr-rose-deep); font-weight:700; }
.post-menu { display:grid; gap:8px; }
.reply-meta { justify-content:space-between; }
.attachment { display:flex; align-items:center; gap:5px; margin:8px 0 0; color:var(--hr-ink-2); font-size:13px; }
.attachment svg { width:16px; height:16px; }
.attachment-control,.retry { display:flex; gap:8px; align-items:center; justify-content:space-between; }
.empty h3,.empty p,.guidelines { margin:0 0 4px; }
.compose-filters,.report-options { margin:9px 0 14px; }
.report-options { display:flex; flex-wrap:wrap; gap:7px; }
.discussion-textarea { box-sizing:border-box; width:100%; min-height:100px; padding:9px 10px; border:1px solid var(--hr-line-strong); border-radius:12px; background:var(--hr-surface); font:16px/1.5 var(--hr-font); color:var(--hr-ink); }
.discussion-textarea:focus-within { border-color:var(--hr-rose); }
.text-limit { margin:0; color:var(--hr-ink-2); text-align:right; font-size:12px; }
.reply { padding:2px 0 9px; margin-bottom:8px; border-bottom:1px solid var(--hr-line); }
.more { margin-bottom:12px; }
</style>
