import { request } from './httpClient'
import type { PrivatePhotoPayload } from './privatePhotoService'

export const categories = {
  experience: '运动心得', question: '运动提问', cycle: '周期与运动', training: '动作交流', checkin: '打卡交流'
} as const
export type DiscussionCategory = keyof typeof categories
export type DiscussionView = 'all' | 'saved' | 'mine'
export type DiscussionSort = 'latest' | 'popular'
export type ReactionKind = 'like' | 'save'
export interface DiscussionReactions { like_count: number; liked: boolean; saved: boolean }

export const reportReasons = {
  comparison: '体重或身材比较', body_shaming: '身材羞辱', restriction: '极端节食', personal_info: '泄露个人信息', other: '其他问题'
} as const
export type ReportReason = keyof typeof reportReasons

export const sorts = { latest: '最新', popular: '热门' } as const
export type DiscussionVisibility = 'public' | 'anonymous'

export interface DiscussionReply {
  public_id: string; body: string; published_at: string; mine: boolean
  visibility: DiscussionVisibility; author: string | null; like_count: number; liked: boolean
}
export interface DiscussionPost extends DiscussionReply, DiscussionReactions {
  title: string; category: DiscussionCategory; activity: string | null; reply_count: number; image_ids: number[]
}
export interface LikeResult { liked: boolean; like_count: number }
interface Page<T> { items: T[]; next_cursor: number | null }
interface DiscussionPage extends Page<DiscussionPost> { next_cursor_likes?: number | null }
interface PostText { title: string; body: string; category: DiscussionCategory }
interface PostDraft extends PostText { checkin_id?: number; client_key: string; visibility?: DiscussionVisibility; images?: PrivatePhotoPayload[] }
interface FeedQuery {
  q?: string; category?: DiscussionCategory; cursor?: number; cursor_likes?: number
  view: DiscussionView; sort: DiscussionSort
}

const posts = '/herlog/exercise/discussion/posts'
const postPath = (id: string) => posts + '/' + encodeURIComponent(id)
const replyPath = (postId: string, replyId: string) => postPath(postId) + '/replies/' + encodeURIComponent(replyId)

export const postImagePath = (postId: string, imageId: number) => postPath(postId) + "/images/" + imageId

export const listDiscussion = (query: FeedQuery) =>
  request<DiscussionPage>(posts, { data: { ...query } })
export const createDiscussion = (draft: PostDraft) =>
  request<DiscussionPost>(posts, { method: 'POST', data: { ...draft } })
export const editDiscussion = (id: string, text: PostText) =>
  request<null>(postPath(id), { method: 'PUT', data: { ...text } })
export const setDiscussionReaction = (id: string, kind: ReactionKind, enabled: boolean) =>
  request<DiscussionReactions>(postPath(id) + '/reactions/' + kind, { method: enabled ? 'PUT' : 'DELETE' })
export const listDiscussionReplies = (id: string, cursor?: number) =>
  request<Page<DiscussionReply>>(postPath(id) + '/replies', { data: cursor ? { cursor } : {} })
export const sendDiscussionReply = (id: string, body: string, client_key: string, visibility: DiscussionVisibility = "anonymous") =>
  request<DiscussionReply>(postPath(id) + '/replies', { method: 'POST', data: { body, client_key, visibility } })
export const likeDiscussionReply = (postId: string, replyId: string) =>
  request<LikeResult>(replyPath(postId, replyId) + '/like', { method: 'POST' })
export const unlikeDiscussionReply = (postId: string, replyId: string) =>
  request<LikeResult>(replyPath(postId, replyId) + '/like', { method: 'DELETE' })
export const removeDiscussionItem = (postId: string, replyId?: string) =>
  request<null>(replyId ? replyPath(postId, replyId) : postPath(postId), { method: 'DELETE' })
export const reportDiscussionItem = (postId: string, reason_code: ReportReason, replyId?: string) =>
  request<null>((replyId ? replyPath(postId, replyId) : postPath(postId)) + '/reports', { method: 'POST', data: { reason_code } })
