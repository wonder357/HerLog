import type { EncodedImage } from './image'

/** 持有一张压缩照片。分析重试复用原始记录时间和这一份编码。 */
export interface SkinDraft {
  site: string
  capturedAt: string
  image: EncodedImage
}
