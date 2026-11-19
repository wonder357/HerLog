/**
 * 选图与缩放（H5）。拍照后先缩到 1024 长边并重编码 JPEG，再按 base64 上传，
 * 保证发送给模型前不超出 3 MiB 与像素上限。
 */

export interface EncodedImage {
  base64: string
  mime: 'image/jpeg'
  previewUrl: string
}

const MAX_SIDE = 1024
const QUALITY = 0.85
const MAX_BYTES = 3 * 1024 * 1024
const MAX_PIXELS = 40_000_000

function loadImage(src: string): Promise<HTMLImageElement> {
  return new Promise((resolve, reject) => {
    const image = new Image()
    image.onload = () => resolve(image)
    image.onerror = () => reject(new Error('图片读取失败，请重新选择'))
    image.src = src
  })
}

export function chooseImage(source?: 'camera' | 'album'): Promise<string | null> {
  return new Promise((resolve, reject) => {
    uni.chooseImage({
      count: 1,
      sizeType: ['original'],
      sourceType: source ? [source] : ['camera', 'album'],
      success: (result) => {
        const paths = result.tempFilePaths as string[]
        resolve(paths[0] ?? null)
      },
      fail: (error) => {
        if (/cancel/i.test(error.errMsg)) {
          resolve(null)
          return
        }
        reject(new Error('无法打开照片，请重新选择'))
      }
    })
  })
}

export async function encodeJpeg(path: string, maxSide = MAX_SIDE): Promise<EncodedImage> {
  const image = await loadImage(path)
  const { naturalWidth, naturalHeight } = image
  if (!naturalWidth || !naturalHeight || naturalWidth * naturalHeight > MAX_PIXELS) {
    throw new Error('图片尺寸过大或无法读取，请换一张')
  }
  const scale = Math.min(1, maxSide / Math.max(naturalWidth, naturalHeight))
  const width = Math.max(1, Math.round(naturalWidth * scale))
  const height = Math.max(1, Math.round(naturalHeight * scale))
  const canvas = document.createElement('canvas')
  canvas.width = width
  canvas.height = height
  const context = canvas.getContext('2d')
  if (!context) {
    throw new Error('当前浏览器无法处理图片')
  }
  context.drawImage(image, 0, 0, width, height)
  const blob = await new Promise<Blob>((resolve, reject) => {
    canvas.toBlob((encoded) => {
      if (encoded?.type === 'image/jpeg') resolve(encoded)
      else reject(new Error('图片编码失败，请重试'))
    }, 'image/jpeg', QUALITY)
  })
  if (blob.size > MAX_BYTES) {
    throw new Error('图片超过 3 MiB，请换一张')
  }
  const dataUrl = await new Promise<string>((resolve, reject) => {
    const reader = new FileReader()
    reader.onload = () => resolve(String(reader.result))
    reader.onerror = () => reject(new Error('图片读取失败，请重新选择'))
    reader.readAsDataURL(blob)
  })
  const base64 = dataUrl.split(',')[1] ?? ''
  if (!base64) {
    throw new Error('图片编码失败，请重试')
  }
  return { base64, mime: 'image/jpeg', previewUrl: URL.createObjectURL(blob) }
}
