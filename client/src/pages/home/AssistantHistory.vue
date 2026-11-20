<template>
  <dialog ref="drawer" class="history-drawer" aria-labelledby="assistant-history-title"
    @cancel.prevent="emit('close')" @click="backdrop">
    <header class="drawer-head">
      <h2 id="assistant-history-title">历史对话</h2>
      <H5Button class="icon-button" aria-label="关闭历史" @click="emit('close')"><HerlogIcon name="close" /></H5Button>
    </header>
    <H5Button class="drawer-new" @click="emit('newChat')"><HerlogIcon name="plus" />新建对话</H5Button>
    <H5Form class="history-search" role="search" aria-label="历史对话" @submit.prevent="search">
      <div class="search-field">
        <HerlogIcon name="search" />
        <H5Input ref="searchInput" v-model="query" class="search-input" type="search" aria-label="搜索对话标题"
          placeholder="搜索对话标题" enterkeyhint="search" autocomplete="off" maxlength="24"
          @keydown.enter="guardComposition" />
        <H5Button v-if="query || keyword" class="search-clear" aria-label="清除搜索" @click="clearSearch">
          <HerlogIcon name="close" />
        </H5Button>
      </div>
      <H5Button type="submit" class="search-submit">搜索</H5Button>
    </H5Form>
    <div class="history-list" :aria-busy="loading">
      <p v-if="loading && !rows.length" class="drawer-hint" role="status">正在读取历史…</p>
      <p v-else-if="error" class="drawer-hint" role="alert">{{ error }}
        <H5Button class="hr-action" @click="load()">重试</H5Button>
      </p>
      <p v-else-if="!rows.length" class="drawer-hint">{{ keyword ? '没有匹配的对话标题。' : '开启保存后，发送过的对话会出现在这里。' }}</p>
      <section v-for="group in groups" :key="group.name" :aria-label="group.name" class="history-group">
        <h3>{{ group.name }}</h3>
        <div v-for="row in group.items" :key="row.id" class="history-row" :class="{ current: row.id === activeId }">
          <H5Button class="history-title" :aria-current="row.id === activeId ? 'true' : undefined" @click="emit('open', row)">
            <strong>{{ row.title }}</strong>
            <small>{{ row.id === activeId ? '正在查看' : formatMoment(row.updated_at) }}</small>
          </H5Button>
          <H5Button class="more-menu" :aria-label="'管理对话，' + row.title" @click="emit('manage', row)"><HerlogIcon name="more" /></H5Button>
        </div>
      </section>
      <H5Button v-if="cursor" class="hr-action" :disabled="loading" @click="load(true)">{{ loading ? '正在加载…' : '查看更多' }}</H5Button>
    </div>
    <footer class="drawer-footer">
      <span>历史仅本人可见</span>
      <H5Button class="hr-action" @click="emit('settings')">保存设置</H5Button>
    </footer>
  </dialog>
</template>

<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import H5Button from '../../components/H5Button'
import H5Form from '../../components/H5Form'
import H5Input from '../../components/H5Input'
import HerlogIcon from '../../components/HerlogIcon.vue'
import { currentEpoch } from '../../services/httpClient'
import { listConversations } from '../../services/assistantService'
import type { AssistantConversation } from '../../services/assistantService'
import { diffDays, formatMoment, shanghaiDayKey, todayString } from '../../shared/dates'

defineProps<{ activeId?: string }>()
const emit = defineEmits<{
  close: []; newChat: []; settings: []; open: [row: AssistantConversation]; manage: [row: AssistantConversation]
}>()
const drawer = ref<HTMLDialogElement | null>(null)
const searchInput = ref<{ focus(): void } | null>(null)
const query = ref('')
const keyword = ref('')
const rows = ref<AssistantConversation[]>([])
const cursor = ref<string | null>(null)
const loading = ref(false)
const error = ref('')
let generation = 0
const groups = computed(() => {
  const today = todayString()
  const grouped = [
    { name: '今天', items: [] as AssistantConversation[] },
    { name: '最近 7 天', items: [] as AssistantConversation[] },
    { name: '更早', items: [] as AssistantConversation[] },
  ]
  for (const row of rows.value) {
    const days = diffDays(today, shanghaiDayKey(row.updated_at))
    grouped[days <= 0 ? 0 : days < 7 ? 1 : 2].items.push(row)
  }
  return grouped.filter(group => group.items.length)
})

onMounted(() => {
  drawer.value?.showModal()
  void load()
})
onBeforeUnmount(() => {
  generation += 1
  drawer.value?.close()
})

function backdrop(event: MouseEvent) {
  if (event.target !== drawer.value || !drawer.value) return
  const bounds = drawer.value.getBoundingClientRect()
  if (event.clientX > bounds.right || event.clientX < bounds.left) emit('close')
}

function search() {
  keyword.value = query.value.trim()
  rows.value = []
  cursor.value = null
  void load()
}

function clearSearch() {
  query.value = ''
  searchInput.value?.focus()
  if (keyword.value) search()
}

function guardComposition(event: KeyboardEvent) {
  if (event.isComposing || event.keyCode === 229) event.preventDefault()
}

async function load(append = false) {
  if (append && (loading.value || !cursor.value)) return
  const request = ++generation
  const epoch = currentEpoch()
  const active = () => request === generation && epoch === currentEpoch()
  loading.value = true
  error.value = ''
  try {
    const result = await listConversations(keyword.value, append ? cursor.value ?? undefined : undefined)
    if (!active()) return
    const existing = new Set(append ? rows.value.map(row => row.id) : [])
    rows.value = append ? [...rows.value, ...result.items.filter(row => !existing.has(row.id))] : result.items
    cursor.value = result.next_cursor
  } catch {
    if (active()) error.value = '暂时无法读取历史。'
  } finally {
    if (active()) loading.value = false
  }
}
</script>

<style scoped>
.history-drawer { position:fixed; inset:0 auto 0 max(0px, calc((100% - var(--hr-shell-width)) / 2)); width:min(324px, calc(100vw - 38px)); max-width:none; height:100%; max-height:none; margin:0; padding:0; border:0; border-radius:0 20px 20px 0; background:var(--hr-surface); color:var(--hr-ink); box-shadow:12px 0 30px -18px #412c3275; overflow:hidden; }
.history-drawer[open] { display:grid; grid-template-rows:auto auto auto minmax(0,1fr) auto; }
.history-drawer::backdrop { background:#39263060; }
.drawer-head,.drawer-footer { display:flex; align-items:center; justify-content:space-between; gap:8px; padding:8px 13px; }
.drawer-head { padding-top:max(8px, env(safe-area-inset-top)); border-bottom:1px solid var(--hr-line); }
.drawer-head h2 { margin:0; font:700 18px var(--hr-font); }
.icon-button,.more-menu { width:44px; height:44px; display:grid; place-items:center; border:0; border-radius:12px; background:var(--hr-paper-deep); color:var(--hr-rose-deep); }
.icon-button svg,.drawer-new svg { width:18px; height:18px; }
.drawer-new { display:flex; gap:5px; align-items:center; justify-content:center; min-height:44px; margin:12px 13px 8px; border:0; border-radius:12px; background:var(--hr-rose-soft); color:var(--hr-rose-deep); font:650 14px var(--hr-font); }
.history-search { margin:4px 13px 8px; display:grid; grid-template-columns:minmax(0,1fr) auto; gap:8px; }
.search-field { display:flex; align-items:center; min-width:0; padding-inline-start:12px; border:1px solid var(--hr-line-strong); border-radius:999px; background:var(--hr-paper); }
.search-field:focus-within { border-color:var(--hr-rose); box-shadow:0 0 0 2px var(--hr-rose-soft); }
.search-field > svg { flex:0 0 17px; width:17px; height:17px; color:var(--hr-ink-2); }
.search-input { appearance:none; flex:1 1 0; width:0; min-width:0; min-height:44px; border:0; outline:none; background:transparent; color:var(--hr-ink); padding:0 8px; font:16px/1.4 var(--hr-font); }
.search-input::placeholder { color:var(--hr-ink-2); }
.search-input::-webkit-search-cancel-button { appearance:none; }
.search-clear,.search-submit { min-width:44px; min-height:44px; border:0; border-radius:999px; touch-action:manipulation; }
.search-clear { display:grid; flex:0 0 44px; place-items:center; padding:0; background:transparent; color:var(--hr-ink-2); }
.search-clear svg { width:16px; height:16px; }
.search-submit { padding:0 14px; background:var(--hr-paper-deep); color:var(--hr-rose-deep); font:650 14px/1.4 var(--hr-font); white-space:nowrap; }
.history-list { padding:0 13px 8px; overflow:auto; overscroll-behavior:contain; }
.history-group h3,.drawer-hint,.drawer-footer { color:var(--hr-ink-2); font:13px/1.5 var(--hr-font); }
.history-group h3 { margin:11px 1px 5px; }
.history-row { display:grid; grid-template-columns:minmax(0,1fr) 44px; align-items:center; border:1px solid transparent; border-radius:11px; margin-bottom:4px; }
.history-row.current { background:var(--hr-rose-soft); border-color:var(--hr-line-strong); }
.history-title { display:grid; min-width:0; min-height:52px; gap:2px; align-content:center; padding:5px 8px; border:0; border-radius:8px; background:transparent; color:var(--hr-ink); text-align:left; font:14px/20px var(--hr-font); touch-action:manipulation; }
.history-title strong { overflow:hidden; white-space:nowrap; text-overflow:ellipsis; }
.history-title small { color:var(--hr-ink-2); font:12px/18px var(--hr-font); }
.more-menu { background:transparent; padding:0; }
.more-menu svg { display:block; width:20px; height:20px; }
.drawer-footer { border-top:1px solid var(--hr-line); padding-block-end:max(8px, env(safe-area-inset-bottom)); }
</style>
