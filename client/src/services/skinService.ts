import { fetchBlobUrl, releaseBlobUrl, request } from './httpClient'
import type { SkinAnalysis, SkinObservation, SkinSummaryItem } from './types'

export interface AnalyzePayload {
  site: string
  captured_at: string
  mime: 'image/jpeg' | 'image/png'
  image_base64: string
}

export function analyze(payload: AnalyzePayload): Promise<SkinAnalysis> {
  return request<SkinAnalysis>('/herlog/skin/analyze', {
    method: 'POST',
    data: payload as unknown as Record<string, unknown>
  })
}

/** 放弃或重拍只释放暂存，不进历史。 */
export function discardPending(analysisId: string): Promise<null> {
  return request<null>(`/herlog/skin/pending/${analysisId}`, { method: 'DELETE' })
}

export function saveObservation(analysisId: string): Promise<SkinObservation> {
  return request<SkinObservation>('/herlog/skin/observations', {
    method: 'POST',
    data: { analysis_id: analysisId }
  })
}

export function listObservations(query: {
  site?: string
  from?: string
  to?: string
} = {}): Promise<SkinSummaryItem[]> {
  const data: Record<string, unknown> = {}
  if (query.site) data.site = query.site
  if (query.from) data.from = query.from
  if (query.to) data.to = query.to
  return request<SkinSummaryItem[]>('/herlog/skin/observations', { data })
}

export function getObservation(id: number): Promise<SkinObservation> {
  return request<SkinObservation>(`/herlog/skin/observations/${id}`)
}

/** 图片需要 token，H5 用鉴权请求取回后转临时对象 URL。 */
export function observationImageUrl(id: number): Promise<string> {
  return fetchBlobUrl(`/herlog/skin/observations/${id}/image`)
}

export { releaseBlobUrl }

export const SKIN_SITES = ['面部', '额头', '下巴', '脸颊', '颈部', '背部', '胸口', '手臂', '其他']

export const SKIN_FLOWS = {
  notice: '照片会发送给模型服务，仅用于本次观察，确认保存后才会写入历史。',
  saving: '保存中…',
  analyzing: '正在分析…'
}
