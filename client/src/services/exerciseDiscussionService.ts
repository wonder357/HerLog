import { request } from './httpClient'
import type { PrivatePhotoPayload } from './privatePhotoService'

export const categories = { experience: '运动心得', question: '运动提问', checkin: '打卡交流' } as const
export type DiscussionCategory = keyof typeof categories

export const reportReasons = {
  comparison: '体重或身材比较', body_shaming: '身材羞辱', restriction: '极端节食', personal_info: '泄露个人信息', other: '其他问题'
} as const
export type ReportReason = keyof typeof reportReasons

export const sorts = { latest: '最新', popular: '热门' } as const
export type DiscussionSort = keyof typeof sorts
export type DiscussionVisibility = 'public' | 'anonymous'

export interface DiscussionReply {
  public_id: string; body: string; published_at: string; mine: boolean
  visibility: DiscussionVisibility; author: string | null; like_count: number; liked: boolean
}
export interface DiscussionPost extends DiscussionReply {
  title: string; category: DiscussionCategory; activity: string | null; reply_count: number; image_ids: number[]
}
export interface LikeResult { liked: boolean; like_count: number }
interface Page<T> { items: T[]; next_cursor: number | null }
interface PostDraft {
  title: string; body: string; category: DiscussionCategory; client_key: string
  visibility: DiscussionVisibility; checkin_id?: number; images?: PrivatePhotoPayload[]
}
interface FeedQuery {
  category?: DiscussionCategory; sort?: DiscussionSort; mine?: boolean; cursor?: number
}

const posts = '/herlog/exercise/discussion/posts'
const postPath = (id: string) => posts + '/' + encodeURIComponent(id)
const replyPath = (postId: string, replyId: string) => postPath(postId) + '/replies/' + encodeURIComponent(replyId)

export const postImagePath = (postId: string, imageId: number) =>
  postPath(postId) + '/images/' + encodeURIComponent(String(imageId))

export const listDiscussion = (query: FeedQuery = {}) =>
  request<Page<DiscussionPost>>(posts, {
    data: {
      ...(query.category ? { category: query.category } : {}),
      ...(query.sort && query.sort !== 'latest' ? { sort: query.sort } : {}),
      ...(query.mine ? { scope: 'mine' } : {}),
      ...(query.cursor ? { cursor: query.cursor } : {})
    }
  })
export const createDiscussion = (draft: PostDraft) =>
  request<DiscussionPost>(posts, { method: 'POST', data: { ...draft } })
export const likeDiscussion = (id: string) =>
  request<LikeResult>(postPath(id) + '/like', { method: 'POST' })
export const unlikeDiscussion = (id: string) =>
  request<LikeResult>(postPath(id) + '/like', { method: 'DELETE' })
export const listDiscussionReplies = (id: string, cursor?: number) =>
  request<Page<DiscussionReply>>(postPath(id) + '/replies', { data: cursor ? { cursor } : {} })
export const sendDiscussionReply = (id: string, body: string, client_key: string, visibility: DiscussionVisibility) =>
  request<DiscussionReply>(postPath(id) + '/replies', { method: 'POST', data: { body, client_key, visibility } })
export const likeDiscussionReply = (postId: string, replyId: string) =>
  request<LikeResult>(replyPath(postId, replyId) + '/like', { method: 'POST' })
export const unlikeDiscussionReply = (postId: string, replyId: string) =>
  request<LikeResult>(replyPath(postId, replyId) + '/like', { method: 'DELETE' })
export const removeDiscussionItem = (postId: string, replyId?: string) =>
  request<null>(replyId ? replyPath(postId, replyId) : postPath(postId), { method: 'DELETE' })
export const reportDiscussionItem = (postId: string, reason_code: ReportReason, replyId?: string) =>
  request<null>((replyId ? replyPath(postId, replyId) : postPath(postId)) + '/reports', { method: 'POST', data: { reason_code } })
