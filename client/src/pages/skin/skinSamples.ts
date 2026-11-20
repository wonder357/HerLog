export interface SkinSample {
  site: string
  note: string
  src: string
  alt: string
}

/**
 * 拍照示例（展示用）：按部位给出取景范围、光线与常见可见状态。
 * 图片放在 static/demo/，只用于说明怎么拍，不参与分析和上传。
 */
export const SKIN_SAMPLES: SkinSample[] = [
  {
    site: '面部',
    note: '窗边自然光，正对镜头',
    src: '/static/demo/demo-skin-face-window.jpg',
    alt: '面部示例：窗边自然光下的正面近景'
  },
  {
    site: '面部',
    note: '室内暖光，光线偏暗也能记录',
    src: '/static/demo/demo-skin-face-warm.jpg',
    alt: '面部示例：室内暖光下的正面近景'
  },
  {
    site: '手部',
    note: '掌心平摊，纹路清晰',
    src: '/static/demo/demo-skin-hand-palm.jpg',
    alt: '手部示例：掌心朝向镜头的平摊手掌'
  },
  {
    site: '手部',
    note: '手背斜放，指节入框',
    src: '/static/demo/demo-skin-hand-back.jpg',
    alt: '手部示例：手背朝向镜头的手指'
  },
  {
    site: '腿部',
    note: '坐姿屈膝，小腿整体入框',
    src: '/static/demo/demo-skin-leg-window.jpg',
    alt: '腿部示例：坐姿屈膝的小腿近景'
  },
  {
    site: '腿部',
    note: '靠近拍局部，泛红看得更清楚',
    src: '/static/demo/demo-skin-leg-flush.jpg',
    alt: '腿部示例：靠近拍摄的小腿局部泛红'
  },
  {
    site: '腿部',
    note: '自然光下拍整段小腿',
    src: '/static/demo/demo-skin-leg-bed.jpg',
    alt: '腿部示例：明亮光线下的整段小腿'
  }
]
