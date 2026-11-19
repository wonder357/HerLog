import { reactive } from 'vue'
import type { SkinAnalysis } from '../services/types'

interface SkinDraft {
  analysis: SkinAnalysis | null
  site: string
  previewUrl: string
}

/** 分析结果在页面间传递：只存在内存里，刷新即失效，避免把观察结果写进本地存储。 */
export const skinDraft = reactive<SkinDraft>({
  analysis: null,
  site: '',
  previewUrl: ''
})

export function setSkinDraft(analysis: SkinAnalysis, site: string, previewUrl: string): void {
  skinDraft.analysis = analysis
  skinDraft.site = site
  skinDraft.previewUrl = previewUrl
}

export function clearSkinDraft(): void {
  skinDraft.analysis = null
  skinDraft.site = ''
  skinDraft.previewUrl = ''
}
