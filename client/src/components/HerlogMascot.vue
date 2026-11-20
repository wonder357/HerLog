<template>
  <picture class="hr-mascot" :class="'hr-mascot--' + pose" :style="{ width: size + 'px', height: size + 'px' }">
    <source media="(prefers-reduced-motion: reduce)" :srcset="stills[pose]" />
    <img :src="motion[pose]" :width="size" :height="size" :alt="alt" :aria-hidden="alt ? undefined : 'true'"
      decoding="async" draggable="false" />
  </picture>
</template>

<script setup lang="ts">
/**
 * 卡通形象「小胭」——纸页精灵。
 * 动图取自动图库（assets/mascot/*.gif），系统要求「减少动态效果」时退回同姿态的静态 SVG。
 * 源文件：assets/mascot/（改形改色改那里再重导出），交付件：src/static/mascot/。
 * 用法见 docs/design/她记-卡通形象-小胭.md：最小 24px，表情位 48px 起，不改色、不加投影、不镜像。
 */
const motion = {
  hi: '/static/mascot/mascot-hi.gif',
  idle: '/static/mascot/mascot-idle.gif',
  care: '/static/mascot/mascot-care.gif',
  sleep: '/static/mascot/mascot-sleep.gif',
  oops: '/static/mascot/mascot-oops.gif',
  write: '/static/mascot/mascot-write.gif',
  done: '/static/mascot/mascot-done.gif',
  cheer: '/static/mascot/mascot-cheer.gif'
} as const

/** 静态回退：与动图同姿态的 SVG，供 prefers-reduced-motion 使用 */
const stills: Record<keyof typeof motion, string> = {
  hi: '/static/mascot/mascot-still-normal.svg',
  idle: '/static/mascot/mascot-still-normal.svg',
  care: '/static/mascot/mascot-still-caring.svg',
  sleep: '/static/mascot/mascot-still-sleepy.svg',
  oops: '/static/mascot/mascot-still-caring.svg',
  write: '/static/mascot/mascot-still-normal.svg',
  done: '/static/mascot/mascot-still-normal.svg',
  cheer: '/static/mascot/mascot-still-normal.svg'
}

withDefaults(defineProps<{
  /** 动作：打招呼 · 平常 · 关心 · 睡觉 · 失误 · 记录 · 记好了 · 庆祝 */
  pose?: keyof typeof motion
  /** 渲染边长（px），等比缩放；动图为方块 */
  size?: number
  /** 有语义时给替代文字；留空表示纯装饰，对读屏隐藏 */
  alt?: string
}>(), { pose: 'idle', size: 72, alt: '' })
</script>

<style scoped>
.hr-mascot {
  display: block;
  flex: none;
  line-height: 0;
}
.hr-mascot img {
  display: block;
  width: 100%;
  height: 100%;
  object-fit: contain;
  -webkit-user-select: none;
  user-select: none;
  -webkit-user-drag: none;
}
</style>
