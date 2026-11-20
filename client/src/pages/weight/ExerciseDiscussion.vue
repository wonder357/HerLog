<template>
  <div class="discussion">
    <header class="card discussion-head">
      <div class="head-copy">
        <p class="eyebrow">运动讨论区</p>
        <h2>一起聊聊怎么动</h2>
        <p>公开或匿名都可以发帖；支持图片、点赞和回复，所有登录用户可见。</p>
      </div>
      <H5Button class="primary" @click="openCompose()">发帖</H5Button>
    </header>

    <div class="discussion-tools">
      <div class="filters" role="group" aria-label="筛选话题">
        <H5Button class="chip" :aria-pressed="!filter" @click="changeCategory()">全部</H5Button>
        <H5Button v-for="(label, code) in categories" :key="code" class="chip"
          :aria-pressed="filter === code" @click="changeCategory(code)">{{ label }}</H5Button>
      </div>
      <div class="switches" role="group" aria-label="排序与范围">
        <H5Button v-for="(label, code) in sorts" :key="code" class="chip" :aria-pressed="sort === code"
          @click="changeSort(code)">{{ label }}</H5Button>
        <H5Button class="chip" :aria-pressed="mineOnly" @click="toggleMine">我的</H5Button>
      </div>
    </div>

    <p v-if="loading && !posts.length" class="card muted" role="status">正在读取讨论…</p>
    <div v-if="feedError" class="card retry" role="alert">
      <span>{{ feedError }}</span><H5Button class="hr-action" @click="loadPosts()">重试</H5Button>
    </div>
    <div v-else-if="!loading && !posts.length" class="card empty">
      <h3>{{ emptyTitle }}</h3>
      <p class="muted">可以从一次活动体验、一张运动照片，或一个想请教的问题开始。</p>
    </div>

    <article v-for="post in posts" :key="post.public_id" class="card discussion-post">
      <div class="post-meta">
        <span class="category">{{ categories[post.category] }}</span>
        <span class="author" :class="{ anonymous: post.visibility === 'anonymous' }">{{ authorLabel(post) }}</span>
        <span class="meta-text">{{ formatMoment(post.published_at) }}</span>
        <span v-if="post.mine" class="badge mine">我发布的</span>
        <span v-if="post.activity" class="badge activity"><HerlogIcon name="walk" />{{ post.activity }}</span>
      </div>
      <h3>{{ post.title }}</h3>
      <p class="post-body">{{ post.body }}</p>
      <div v-if="post.image_ids.length" class="post-images" :class="'count-' + imageLayout(post.image_ids.length)">
        <button v-for="(imageId, index) in post.image_ids" :key="imageId" type="button" class="post-image"
          :aria-label="`查看${post.title}的第 ${index + 1} 张图片`" @click="openViewer(post, index)">
          <img v-if="imageUrl(imageId)" :src="imageUrl(imageId)" alt="" />
          <span v-else class="image-skeleton" aria-hidden="true" />
        </button>
      </div>
      <div class="post-actions">
        <H5Button class="hr-action like" :class="{ chosen: post.liked }" :aria-pressed="post.liked"
          :aria-label="post.liked ? '取消点赞' : '点赞'" @click="toggleLike(post)">
          <HerlogIcon name="heart" /><span>{{ post.like_count || '赞' }}</span>
        </H5Button>
        <H5Button class="hr-action" @click="openThread(post)">
          <HerlogIcon name="comment" /><span>{{ post.reply_count || '回复' }}</span>
        </H5Button>
        <H5Button class="hr-action" @click="chooseAction(post, post.mine ? 'remove' : 'report')">
          {{ post.mine ? '撤回' : '举报' }}
        </H5Button>
      </div>
    </article>
    <H5Button v-if="postCursor !== null" class="ghost more" :disabled="loading" @click="loadPosts(true)">
      {{ loading ? '正在加载…' : '更多讨论' }}
    </H5Button>

    <HerlogSheet v-if="overlay === 'compose'" title="发起讨论"
      :context="visibility === 'public' ? '公开身份：展示昵称' : '匿名身份：只显示匿名成员'" :busy="busy" @close="closeCompose">
      <p class="muted guidelines">请围绕运动体验交流，避免填写体重、体脂数字、联系方式或极端节食方法。</p>
      <div class="segmented" role="group" aria-label="发布身份">
        <H5Button class="segment" :aria-pressed="visibility === 'public'" :disabled="busy"
          @click="setVisibility('public')">公开</H5Button>
        <H5Button class="segment" :aria-pressed="visibility === 'anonymous'" :disabled="busy"
          @click="setVisibility('anonymous')">匿名</H5Button>
      </div>
      <p class="hint">{{ visibility === 'public' ? '帖子会显示你的昵称「' + nickname + '」。' : '帖子只显示「匿名成员」，你仍然可以撤回它。' }}</p>
      <div class="filters compose-filters" role="group" aria-label="选择话题">
        <H5Button v-for="(label, code) in categories" :key="code" class="chip"
          :aria-pressed="category === code" :disabled="busy" @click="category = code">{{ label }}</H5Button>
      </div>
      <H5Label class="hr-field-label" for="discussion-title">标题</H5Label>
      <H5Input id="discussion-title" v-model="title" class="field" placeholder="例如，晚饭后散步的感受" maxlength="60" :disabled="busy" />
      <p class="hr-field-label field-head">内容 <span class="counter">{{ body.length }}/600</span></p>
      <textarea v-model="body" aria-label="讨论内容" class="discussion-textarea post-input" maxlength="600" :disabled="busy" />
      <div class="image-tools">
        <H5Button class="chip" :disabled="busy || mediaBusy || images.length >= maxImages" @click="addImages()">
          {{ mediaBusy ? '正在处理图片…' : images.length ? '再加一张' : '添加图片' }}
        </H5Button>
        <span class="hint">{{ images.length }}/{{ maxImages }} 张，支持相册或拍照</span>
      </div>
      <div v-if="images.length" class="draft-images">
        <div v-for="(image, index) in images" :key="image.previewUrl" class="draft-image">
          <img :src="image.previewUrl" alt="" />
          <H5Button class="remove" :disabled="busy" :aria-label="`移除第 ${index + 1} 张图片`"
            @click="removeImage(index)">×</H5Button>
        </div>
      </div>
      <div v-if="attachment" class="attachment-control">
        <p class="attachment"><HerlogIcon name="walk" />打卡项目 · {{ attachment.activity }}</p>
        <H5Button class="hr-action" :disabled="busy" @click="attachment = null">移除打卡</H5Button>
      </div>
      <p v-if="actionError" class="error" role="alert">{{ actionError }}</p>
      <template #actions>
        <H5Button class="primary" :disabled="publishing || title.trim().length < 2 || !body.trim()" @click="publish">
          {{ busy ? '正在发布…' : visibility === 'public' ? '公开发布' : '匿名发布' }}
        </H5Button>
      </template>
    </HerlogSheet>

    <HerlogSheet v-if="overlay === 'thread' && thread" title="讨论回复"
      :context="authorLabel(thread) + ' · ' + thread.title" :busy="busy" @close="overlay = null">
      <p class="post-body thread-original">{{ thread.body }}</p>
      <div v-if="thread.image_ids.length" class="post-images thread-images"
        :class="'count-' + imageLayout(thread.image_ids.length)">
        <button v-for="(imageId, index) in thread.image_ids" :key="imageId" type="button" class="post-image"
          :aria-label="`查看第 ${index + 1} 张图片`" @click="openViewer(thread, index)">
          <img v-if="imageUrl(imageId)" :src="imageUrl(imageId)" alt="" />
          <span v-else class="image-skeleton" aria-hidden="true" />
        </button>
      </div>
      <div class="thread-stats">
        <H5Button class="hr-action like" :class="{ chosen: thread.liked }" :aria-pressed="thread.liked"
          @click="toggleLike(thread)"><HerlogIcon name="heart" /><span>{{ thread.like_count || '赞' }}</span></H5Button>
        <span class="hint">{{ thread.reply_count }} 条回复</span>
      </div>
      <p v-if="repliesLoading && !replies.length" class="muted" role="status">正在读取回复…</p>
      <div v-if="replyError" class="retry" role="alert">
        <span>{{ replyError }}</span><H5Button class="hr-action" @click="loadReplies()">重试</H5Button>
      </div>
      <p v-else-if="!repliesLoading && !replies.length" class="muted">还没有回复，可以聊聊自己的体验。</p>
      <div v-for="reply in replies" :key="reply.public_id" class="reply">
        <div class="reply-meta">
          <span class="author" :class="{ anonymous: reply.visibility === 'anonymous' }">{{ authorLabel(reply) }}</span>
          <span class="meta-text">{{ formatMoment(reply.published_at) }}</span>
        </div>
        <p class="post-body">{{ reply.body }}</p>
        <div class="reply-actions">
          <H5Button class="hr-action like" :class="{ chosen: reply.liked }" :aria-pressed="reply.liked"
            :aria-label="reply.liked ? '取消有用' : '标记有用'" @click="toggleReplyLike(reply)">
            <HerlogIcon name="heart" /><span>{{ reply.like_count || '有用' }}</span>
          </H5Button>
          <H5Button class="hr-action" :disabled="busy" @click="chooseAction(thread!, reply.mine ? 'remove' : 'report', reply)">
            {{ reply.mine ? '撤回回复' : '举报回复' }}
          </H5Button>
        </div>
      </div>
      <H5Button v-if="replyCursor !== null" class="hr-action" :disabled="repliesLoading" @click="loadReplies(true)">更多回复</H5Button>
      <div class="reply-compose">
        <div class="segmented small" role="group" aria-label="回复身份">
          <H5Button class="segment" :aria-pressed="replyVisibility === 'public'" :disabled="busy"
            @click="replyVisibility = 'public'">公开回复</H5Button>
          <H5Button class="segment" :aria-pressed="replyVisibility === 'anonymous'" :disabled="busy"
            @click="replyVisibility = 'anonymous'">匿名回复</H5Button>
        </div>
        <textarea v-model="replyBody" aria-label="回复内容" class="discussion-textarea reply-input"
          maxlength="300" :disabled="busy" />
      </div>
      <p v-if="actionError" class="error" role="alert">{{ actionError }}</p>
      <template #actions>
        <H5Button class="primary" :disabled="publishing || !replyBody.trim()" @click="publishReply">
          {{ busy ? '正在发送…' : replyVisibility === 'public' ? '公开回复' : '匿名回复' }}
        </H5Button>
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

    <view v-if="viewer" class="viewer" role="dialog" aria-modal="true" aria-label="查看图片">
      <button type="button" class="viewer-hit" aria-label="关闭图片" @click="closeViewer" />
      <img class="viewer-image" :src="viewer.url" alt="" />
      <p class="viewer-caption">{{ viewer.caption }}</p>
    </view>
  </div>
</template>

<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, reactive, ref, watch } from 'vue'
import H5Button from '../../components/H5Button'
import { H5Label } from '../../components/H5Form'
import H5Input from '../../components/H5Input'
import HerlogIcon from '../../components/HerlogIcon.vue'
import HerlogSheet from '../../components/HerlogSheet.vue'
import { ApiRequestError, currentEpoch, fetchBlobUrl, releaseBlobUrl } from '../../services/httpClient'
import { formatMoment } from '../../shared/dates'
import { newClientKey } from '../../services/weightService'
import { chooseImage, encodeJpeg } from '../../utils/image'
import type { EncodedImage } from '../../utils/image'
import {
  categories, createDiscussion, likeDiscussion, likeDiscussionReply, listDiscussion, listDiscussionReplies,
  postImagePath, removeDiscussionItem, reportDiscussionItem, reportReasons, sendDiscussionReply, sorts,
  unlikeDiscussion, unlikeDiscussionReply
} from '../../services/exerciseDiscussionService'
import type {
  DiscussionCategory, DiscussionPost, DiscussionReply, DiscussionSort, DiscussionVisibility, ReportReason
} from '../../services/exerciseDiscussionService'
import type { ShareReference } from '../../services/wellnessService'
import { useAuthStore } from '../../stores/auth'

const props = defineProps<{ reference: ShareReference | null }>()
const emit = defineEmits<{ clearReference: [] }>()
const auth = useAuthStore()
const maxImages = 3

const filter = ref<DiscussionCategory>()
const sort = ref<DiscussionSort>('latest')
const mineOnly = ref(false)
const posts = ref<DiscussionPost[]>([])
const postCursor = ref<number | null>(null)
const loading = ref(false)
const feedError = ref('')
const overlay = ref<'compose' | 'thread' | 'report' | 'remove' | null>(null)
const title = ref('')
const body = ref('')
const category = ref<DiscussionCategory>('experience')
const visibility = ref<DiscussionVisibility>('anonymous')
const images = ref<EncodedImage[]>([])
const mediaBusy = ref(false)
const attachment = ref<ShareReference | null>(null)
const busy = ref(false)
const publishing = ref(false)
const actionError = ref('')
const thread = ref<DiscussionPost | null>(null)
const replies = ref<DiscussionReply[]>([])
const replyCursor = ref<number | null>(null)
const repliesLoading = ref(false)
const replyError = ref('')
const replyBody = ref('')
const replyVisibility = ref<DiscussionVisibility>('anonymous')
const target = ref<{ post: DiscussionPost; reply?: DiscussionReply } | null>(null)
const reason = ref<ReportReason | null>(null)
const viewer = ref<{ url: string; caption: string } | null>(null)
const imagesById = reactive<Record<number, string>>({})

let postKey = newClientKey()
let replyKey = newClientKey()
let feedRequest = 0
let repliesRequest = 0
const epoch = currentEpoch()
let mounted = true
const active = () => mounted && currentEpoch() === epoch
const pendingImages = new Set<number>()
const nickname = computed(() => auth.member?.name || auth.member?.username || '她记用户')

watch([title, body, category, attachment, visibility], () => { postKey = newClientKey() }, { flush: 'sync' })
watch(replyBody, () => { replyKey = newClientKey() }, { flush: 'sync' })
watch(() => props.reference, reference => {
  if (!reference) return
  attachment.value = reference
  category.value = 'checkin'
  openCompose()
}, { immediate: true })
onBeforeUnmount(() => {
  mounted = false
  Object.values(imagesById).forEach(releaseBlobUrl)
  images.value.forEach(image => releaseBlobUrl(image.previewUrl))
})
onMounted(() => { void loadPosts() })

const emptyTitle = computed(() => {
  if (mineOnly.value) return '你还没有发布过讨论'
  return filter.value ? '这个话题还没有帖子' : '还没有讨论'
})

function authorLabel(item: { visibility: DiscussionVisibility; author: string | null; mine: boolean }) {
  if (item.visibility === 'anonymous') return item.mine ? '匿名成员（我）' : '匿名成员'
  return item.author || '她记用户'
}

function imageLayout(count: number) {
  return Math.min(count, 3)
}

function imageUrl(imageId: number) {
  return imagesById[imageId] || ''
}

function ensureImage(postId: string, imageId: number) {
  if (imagesById[imageId] || pendingImages.has(imageId)) return
  pendingImages.add(imageId)
  fetchBlobUrl(postImagePath(postId, imageId))
    .then(url => { if (active()) imagesById[imageId] = url })
    .catch(() => undefined)
    .finally(() => pendingImages.delete(imageId))
}

function ensurePostImages(list: { public_id: string; image_ids: number[] }[]) {
  list.forEach(post => post.image_ids.forEach(imageId => ensureImage(post.public_id, imageId)))
}

function openViewer(post: { public_id: string; image_ids: number[]; title?: string }, index: number) {
  const imageId = post.image_ids[index]
  if (!imageId) return
  ensureImage(post.public_id, imageId)
  const url = imagesById[imageId]
  if (!url) return
  viewer.value = { url, caption: post.title ? post.title + ' · 第 ' + (index + 1) + ' 张' : '图片 ' + (index + 1) }
}

function closeViewer() { viewer.value = null }

function changeCategory(value?: DiscussionCategory) {
  if (filter.value === value) return
  filter.value = value
  resetFeed()
}

function changeSort(value: DiscussionSort) {
  if (sort.value === value) return
  sort.value = value
  resetFeed()
}

function toggleMine() {
  mineOnly.value = !mineOnly.value
  resetFeed()
}

function resetFeed() {
  posts.value = []
  postCursor.value = null
  void loadPosts()
}

async function loadPosts(append = false) {
  if (append && (loading.value || postCursor.value === null)) return
  const request = ++feedRequest
  const isCurrent = () => active() && request === feedRequest
  loading.value = true
  feedError.value = ''
  try {
    const result = await listDiscussion({
      category: filter.value, sort: sort.value, mine: mineOnly.value,
      cursor: append ? postCursor.value ?? undefined : undefined
    })
    if (!isCurrent()) return
    posts.value = append ? [...posts.value, ...result.items] : result.items
    postCursor.value = result.next_cursor
    ensurePostImages(result.items)
  } catch {
    if (isCurrent()) feedError.value = '讨论列表暂时无法读取。'
  } finally {
    if (isCurrent()) loading.value = false
  }
}

function openCompose() {
  actionError.value = ''
  overlay.value = 'compose'
}

function closeCompose() {
  overlay.value = null
  actionError.value = ''
  emit('clearReference')
}

function setVisibility(value: DiscussionVisibility) {
  visibility.value = value
}

async function addImages() {
  if (mediaBusy.value || images.value.length >= maxImages) return
  mediaBusy.value = true
  actionError.value = ''
  try {
    const path = await chooseImage('album')
    if (!path) return
    const encoded = await encodeJpeg(path)
    if (images.value.length >= maxImages) {
      releaseBlobUrl(encoded.previewUrl)
      actionError.value = '最多只能添加 3 张图片'
      return
    }
    images.value = [...images.value, encoded]
  } catch (failure) {
    actionError.value = failure instanceof Error ? failure.message : '图片处理失败，请重试'
  } finally {
    mediaBusy.value = false
  }
}

function removeImage(index: number) {
  const image = images.value[index]
  if (!image) return
  releaseBlobUrl(image.previewUrl)
  images.value = images.value.filter((_, position) => position !== index)
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
  if (busy.value || !active()) return
  const draftImages = images.value.map(image => ({ mime: image.mime, image_base64: image.base64 } as const))
  busy.value = true
  publishing.value = true
  actionError.value = ''
  void (async () => {
    try {
      const post = await createDiscussion({
        title: title.value.trim(), body: body.value.trim(), category: category.value, client_key: postKey,
        visibility: visibility.value,
        ...(draftImages.length ? { images: draftImages } : {}),
        ...(attachment.value?.checkin_id ? { checkin_id: attachment.value.checkin_id } : {})
      })
      if (!active()) return
      title.value = body.value = ''
      category.value = 'experience'
      attachment.value = null
      images.value.forEach(image => releaseBlobUrl(image.previewUrl))
      images.value = []
      closeCompose()
      if (mineOnly.value || (filter.value && filter.value !== post.category) || sort.value === 'popular') resetFeed()
      else void loadPosts()
      uni.showToast({ title: post.visibility === 'public' ? '已公开发布' : '已匿名发布', icon: 'none' })
    } catch (failure) {
      if (active()) actionError.value = failure instanceof ApiRequestError ? failure.message : '发布暂未完成，可以重试。'
    } finally {
      if (active()) { busy.value = false; publishing.value = false }
    }
  })()
}

function openThread(post: DiscussionPost) {
  thread.value = post
  replies.value = []
  replyCursor.value = null
  replyBody.value = ''
  replyVisibility.value = 'anonymous'
  actionError.value = ''
  overlay.value = 'thread'
  void loadReplies()
}

async function loadReplies(append = false) {
  const post = thread.value
  if (!post || (append && (repliesLoading.value || replyCursor.value === null))) return
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
  const post = thread.value
  if (!post || busy.value) return
  void mutate(async () => {
    await sendDiscussionReply(post.public_id, replyBody.value.trim(), replyKey, replyVisibility.value)
    if (!active()) return
    replyBody.value = ''
    thread.value = { ...post, reply_count: post.reply_count + 1 }
    void loadReplies()
    void loadPosts()
  })
}

function toggleLike(post: DiscussionPost) {
  if (!active()) return
  const next = !post.liked
  const previousCount = post.like_count
  patchPost(post.public_id, { liked: next, like_count: Math.max(0, previousCount + (next ? 1 : -1)) })
  void (async () => {
    try {
      const result = next ? await likeDiscussion(post.public_id) : await unlikeDiscussion(post.public_id)
      if (!active()) return
      patchPost(post.public_id, { liked: result.liked, like_count: result.like_count })
    } catch {
      if (!active()) return
      patchPost(post.public_id, { liked: !next, like_count: previousCount })
      uni.showToast({ title: '点赞没有成功，请稍后再试', icon: 'none' })
    }
  })()
}

function patchPost(publicId: string, patch: Partial<DiscussionPost>) {
  posts.value = posts.value.map(item => item.public_id === publicId ? { ...item, ...patch } : item)
  if (thread.value?.public_id === publicId) thread.value = { ...thread.value, ...patch }
}

function toggleReplyLike(reply: DiscussionReply) {
  const post = thread.value
  if (!post || !active()) return
  const next = !reply.liked
  const previousCount = reply.like_count
  const apply = (values: Partial<DiscussionReply>) => {
    replies.value = replies.value.map(item => item.public_id === reply.public_id ? { ...item, ...values } : item)
  }
  apply({ liked: next, like_count: Math.max(0, previousCount + (next ? 1 : -1)) })
  void (async () => {
    try {
      const result = next
        ? await likeDiscussionReply(post.public_id, reply.public_id)
        : await unlikeDiscussionReply(post.public_id, reply.public_id)
      if (!active()) return
      apply({ liked: result.liked, like_count: result.like_count })
    } catch {
      if (!active()) return
      apply({ liked: !next, like_count: previousCount })
      uni.showToast({ title: '操作没有成功，请稍后再试', icon: 'none' })
    }
  })()
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
.discussion-head p { margin:0; color:var(--hr-ink-2); font-size:13px; line-height:1.55; }
.discussion-head .eyebrow { color:var(--hr-rose-deep); font-weight:650; }
.discussion-head .primary { white-space:nowrap; min-height:44px; width:auto; padding:6px 14px; font-size:13px; }
.discussion-tools { display:grid; gap:6px; margin-bottom:8px; }
.filters,.switches { display:flex; flex-wrap:wrap; gap:6px; }
.chip { min-height:44px; border:1px solid var(--hr-line-strong); border-radius:14px; background:var(--hr-surface); color:var(--hr-ink-2); padding:5px 10px; font-size:13px; }
.chip[aria-pressed='true'] { border-color:var(--hr-rose); background:var(--hr-rose-soft); color:var(--hr-rose-deep); font-weight:650; }
.discussion-post { padding:13px 14px 5px; }
.post-meta { display:flex; align-items:center; flex-wrap:wrap; gap:5px 7px; color:var(--hr-ink-2); font-size:12px; }
.category { padding:2px 7px; border-radius:8px; background:var(--hr-paper-deep); color:var(--hr-ink); }
.author { color:var(--hr-ink); font-weight:600; }
.author.anonymous { color:var(--hr-ink-2); font-weight:500; }
.meta-text { color:var(--hr-ink-2); }
.badge { display:inline-flex; align-items:center; gap:4px; padding:2px 7px; border-radius:999px; font-size:11px; background:var(--hr-paper-deep); color:var(--hr-ink-2); }
.badge.mine { background:var(--hr-rose-soft); color:var(--hr-rose-deep); }
.badge.activity svg { width:14px; height:14px; }
.discussion-post h3,.empty h3 { margin:8px 0 4px; font-size:16px; line-height:1.45; overflow-wrap:anywhere; }
.post-body { white-space:pre-wrap; overflow-wrap:anywhere; line-height:1.65; margin:0; color:var(--hr-ink); font-size:14px; }
.post-images { display:grid; gap:5px; margin-top:9px; }
.post-images.count-1 { grid-template-columns:1fr; }
.post-images.count-2 { grid-template-columns:1fr 1fr; }
.post-images.count-3 { grid-template-columns:repeat(3,minmax(0,1fr)); }
.post-image { position:relative; padding:0; overflow:hidden; border:1px solid var(--hr-line); border-radius:12px; background:var(--hr-paper-deep); aspect-ratio:1/1; cursor:zoom-in; }
.post-images.count-1 .post-image { aspect-ratio:16/10; }
.post-image img { width:100%; height:100%; object-fit:cover; display:block; }
.image-skeleton { display:block; width:100%; height:100%; background:linear-gradient(120deg,var(--hr-paper-deep),var(--hr-rose-soft)); }
.post-actions,.thread-stats { display:flex; align-items:center; gap:10px; margin-top:8px; border-top:1px solid var(--hr-line); padding-top:4px; }
.post-actions .hr-action,.thread-stats .hr-action,.reply-actions .hr-action { display:inline-flex; align-items:center; gap:4px; padding-inline:4px; font-size:13px; color:var(--hr-ink-2); white-space:nowrap; }
.post-actions svg,.thread-stats svg,.reply-actions svg { width:16px; height:16px; flex:0 0 16px; }
.hr-action.like svg { width:16px; height:16px; color:var(--hr-rose); }
.hr-action.like.chosen { color:var(--hr-rose-deep); font-weight:650; }
.hr-action.like.chosen svg { fill:var(--hr-rose); }
.attachment { display:flex; align-items:center; gap:5px; margin:8px 0 0; color:var(--hr-ink-2); font-size:13px; }
.attachment svg { width:16px; height:16px; }
.attachment-control,.retry { display:flex; gap:8px; align-items:center; justify-content:space-between; }
.empty h3,.empty p,.guidelines { margin:0 0 4px; }
.compose-filters,.report-options { margin:9px 0 12px; }
.report-options { display:flex; flex-wrap:wrap; gap:7px; }
.segmented { display:grid; grid-template-columns:1fr 1fr; gap:4px; padding:3px; border-radius:999px; background:var(--hr-paper-deep); }
.segmented.small { max-width:240px; margin-bottom:8px; }
.segment { min-height:40px; border:1px solid transparent; border-radius:999px; background:transparent; color:var(--hr-ink-2); font-size:13px; }
.segment[aria-pressed='true'] { background:var(--hr-surface); border-color:var(--hr-rose); color:var(--hr-rose-deep); font-weight:650; }
.hint { margin:6px 0 0; color:var(--hr-ink-2); font-size:12px; line-height:1.5; }
.field-head { display:flex; align-items:center; justify-content:space-between; gap:8px; }
.counter { color:var(--hr-ink-2); font-size:12px; font-variant-numeric:tabular-nums; }
.image-tools { display:flex; align-items:center; flex-wrap:wrap; gap:8px; margin-top:10px; }
.draft-images { display:grid; grid-template-columns:repeat(3,minmax(0,1fr)); gap:6px; margin-top:8px; }
.draft-image { position:relative; aspect-ratio:1/1; border-radius:10px; overflow:hidden; border:1px solid var(--hr-line); }
.draft-image img { width:100%; height:100%; object-fit:cover; display:block; }
.draft-image .remove { position:absolute; top:3px; right:3px; width:26px; height:26px; min-height:26px; padding:0; border-radius:50%; background:#2b1c22b0; color:#fff; font-size:15px; line-height:1; }
.discussion-textarea { box-sizing:border-box; width:100%; min-height:100px; padding:9px 10px; border:1px solid var(--hr-line-strong); border-radius:12px; background:var(--hr-surface); font:16px/1.5 var(--hr-font); color:var(--hr-ink); }
.discussion-textarea:focus-within { border-color:var(--hr-rose); }
.thread-original { margin:4px 0 8px; padding:10px; border-radius:12px; background:var(--hr-paper-deep); }
.thread-images { margin-bottom:8px; }
.thread-stats { border-top:0; margin:0 0 6px; padding-top:0; }
.reply { padding:2px 0 8px; margin-bottom:8px; border-bottom:1px solid var(--hr-line); }
.reply-meta { display:flex; align-items:center; flex-wrap:wrap; gap:4px 8px; font-size:12px; }
.reply-actions { display:flex; align-items:center; gap:8px; }
.reply-compose { margin-top:10px; }
.more { margin-bottom:12px; }
.viewer { position:fixed; inset:0; z-index:60; display:grid; place-items:center; gap:10px; padding:24px 14px; background:#231a1fdd; }
.viewer-hit { position:absolute; inset:0; border:0; background:transparent; padding:0; }
.viewer-image { position:relative; max-width:100%; max-height:76vh; border-radius:14px; object-fit:contain; }
.viewer-caption { position:relative; margin:0; color:#fff; opacity:.85; font-size:13px; text-align:center; }
</style>
