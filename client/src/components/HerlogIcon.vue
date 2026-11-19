<template>
  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.65" stroke-linecap="round"
    stroke-linejoin="round" aria-hidden="true" focusable="false">
    <path :d="paths[name]" />
  </svg>
</template>

<script setup lang="ts">
const paths = {
  home: 'M4 11.5 12 4l8 7.5V20a1 1 0 0 1-1 1h-4.5v-6h-5v6H5a1 1 0 0 1-1-1z',
  period: 'M5 6h14a1 1 0 0 1 1 1v12a1 1 0 0 1-1 1H5a1 1 0 0 1-1-1V7a1 1 0 0 1 1-1ZM8 3v5m8-5v5M4 10h16m-11 4h1m4 0h1',
  weight: 'm4 17 5-5 3 3 7-8m-5 0h5v5',
  skin: 'M12 3c2 5 4 7 9 9-5 2-7 4-9 9-2-5-4-7-9-9 5-2 7-4 9-9Z',
  me: 'M12 12a4 4 0 1 0 0-8 4 4 0 0 0 0 8zM4 21c0-4 3.6-6 8-6s8 2 8 6',
  send: 'M12 19V5m-5 5 5-5 5 5',
  close: 'm6 6 12 12M18 6 6 18',
  camera: 'M4 7h4l2-2h4l2 2h4v12H4zm11 6a3 3 0 1 1-6 0 3 3 0 0 1 6 0Z',
  walk: 'M13 5a2 2 0 1 1 4 0 2 2 0 0 1-4 0Zm-2 15 3-5-2-3m0 0 3-3 3 3 3 1m-9-1-4 2m1 7 1-4',
  mobility: 'M3 12h3l3-7 4 14 3-7h5',
  strength: 'M5 9v6m-2-5v4m4-7v10m0-5h10m2-5v10m2-8v6m2-5v4',
  cycle: 'M9 17a4 4 0 1 1-8 0 4 4 0 0 1 8 0Zm14 0a4 4 0 1 1-8 0 4 4 0 0 1 8 0ZM5 17l5-9 4 9m-3-9H8m7-2h3l1 3',
  rest: 'M20 15.5A8.5 8.5 0 0 1 8.5 4 8.5 8.5 0 1 0 20 15.5Z',
}
defineProps<{ name: keyof typeof paths }>()
</script>
