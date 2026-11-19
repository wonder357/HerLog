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

function loadImage(src: string): Promise<HTMLImageElement> {
  return new Promise((resolve, reject) => {
    const image = new Image()
    image.onload = () => resolve(image)
    image.onerror = () => reject(new Error('图片读取失败，请重新选择'))
    image.src = src
  })
}

export function chooseImage(): Promise<string> {
  return new Promise((resolve, reject) => {
    uni.chooseImage({
      count: 1,
      sizeType: ['compressed'],
      sourceType: ['camera', 'album'],
      success: (result) => {
        const paths = result.tempFilePaths as string[]
        if (!paths.length) {
          reject(new Error('没有选择图片'))
          return
        }
        resolve(paths[0])
      },
      fail: () => reject(new Error('已取消选择图片'))
    })
  })
}

export async function encodeJpeg(path: string): Promise<EncodedImage> {
  const image = await loadImage(path)
  const scale = Math.min(1, MAX_SIDE / Math.max(image.width, image.height))
  const width = Math.max(1, Math.round(image.width * scale))
  const height = Math.max(1, Math.round(image.height * scale))
  const canvas = document.createElement('canvas')
  canvas.width = width
  canvas.height = height
  const context = canvas.getContext('2d')
  if (!context) {
    throw new Error('当前浏览器无法处理图片')
  }
  context.drawImage(image, 0, 0, width, height)
  const dataUrl = canvas.toDataURL('image/jpeg', QUALITY)
  const base64 = dataUrl.split(',')[1] ?? ''
  if (!base64) {
    throw new Error('图片编码失败，请重试')
  }
  return { base64, mime: 'image/jpeg', previewUrl: dataUrl }
}
