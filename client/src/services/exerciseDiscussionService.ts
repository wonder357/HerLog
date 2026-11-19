import { request } from './httpClient'

export const categories = { experience: '运动心得', question: '运动提问', checkin: '打卡交流' } as const
export type DiscussionCategory = keyof typeof categories

export const reportReasons = {
  comparison: '体重或身材比较', body_shaming: '身材羞辱', restriction: '极端节食', personal_info: '泄露个人信息', other: '其他问题'
} as const
export type ReportReason = keyof typeof reportReasons

export interface DiscussionReply { public_id: string; body: string; published_at: string; mine: boolean }
export interface DiscussionPost extends DiscussionReply {
  title: string; category: DiscussionCategory; activity: string | null; reply_count: number
}
interface Page<T> { items: T[]; next_cursor: number | null }
interface PostDraft { title: string; body: string; category: DiscussionCategory; checkin_id?: number; client_key: string }

const posts = '/herlog/exercise/discussion/posts'
const postPath = (id: string) => posts + '/' + encodeURIComponent(id)
const replyPath = (postId: string, replyId: string) => postPath(postId) + '/replies/' + encodeURIComponent(replyId)

export const listDiscussion = (category?: DiscussionCategory, cursor?: number) =>
  request<Page<DiscussionPost>>(posts, { data: { ...(category ? { category } : {}), ...(cursor ? { cursor } : {}) } })
export const createDiscussion = (draft: PostDraft) =>
  request<DiscussionPost>(posts, { method: 'POST', data: { ...draft } })
export const listDiscussionReplies = (id: string, cursor?: number) =>
  request<Page<DiscussionReply>>(postPath(id) + '/replies', { data: cursor ? { cursor } : {} })
export const sendDiscussionReply = (id: string, body: string, client_key: string) =>
  request<DiscussionReply>(postPath(id) + '/replies', { method: 'POST', data: { body, client_key } })
export const removeDiscussionItem = (postId: string, replyId?: string) =>
  request<null>(replyId ? replyPath(postId, replyId) : postPath(postId), { method: 'DELETE' })
export const reportDiscussionItem = (postId: string, reason_code: ReportReason, replyId?: string) =>
  request<null>((replyId ? replyPath(postId, replyId) : postPath(postId)) + '/reports', { method: 'POST', data: { reason_code } })
