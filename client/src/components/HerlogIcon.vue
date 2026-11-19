<template>
  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.65" stroke-linecap="round"
    stroke-linejoin="round" aria-hidden="true" focusable="false">
    <template v-if="active && name in solidPaths">
      <path :d="solidPaths[name]" fill="currentColor" fill-rule="evenodd" stroke="none" />
    </template>
    <path v-else :d="paths[name]" />
  </svg>
</template>

<script setup lang="ts">
const paths = {
  home: 'M4 11.5 12 4l8 7.5V20a1 1 0 0 1-1 1h-4.5v-6h-5v6H5a1 1 0 0 1-1-1z',
  period: 'M6.5 5.5h11A2.5 2.5 0 0 1 20 8v10a2.5 2.5 0 0 1-2.5 2.5h-11A2.5 2.5 0 0 1 4 18V8a2.5 2.5 0 0 1 2.5-2.5ZM8 3.5v4m8-4v4M4 10h16m-8 2.2c-1.3 1.6-2.3 2.8-2.3 4a2.3 2.3 0 0 0 4.6 0c0-1.2-1-2.4-2.3-4Z',
  weight: 'M7.5 4.5h9a4 4 0 0 1 4 4v7a4 4 0 0 1-4 4h-9a4 4 0 0 1-4-4v-7a4 4 0 0 1 4-4ZM7.7 12a4.4 4.4 0 0 1 8.6 0M12 13l1.6-2.3',
  skin: 'M6.2 20v-4.8a5.5 5.5 0 0 1-1-3.1c0-4.8 3-8.1 7.5-8.1 3.1 0 5.3 2.2 5.3 5.2v1.1l2 3h-2v2.9c0 .8-.6 1.3-1.4 1.3H14v2.5m-7.8-4.8c2.8-1.5 4.7-4.5 4.7-8.1 1.4 1.5 3.7 2.5 6.8 2.5',
  me: 'M12 12a4 4 0 1 0 0-8 4 4 0 0 0 0 8zM4 21c0-4 3.6-6 8-6s8 2 8 6',
  send: 'M12 19V5m-5 5 5-5 5 5',
  chat: 'M20 11.5a8 8 0 0 1-8 8H5l1.5-3A8 8 0 1 1 20 11.5ZM8.5 10h7m-7 3h4.5',
  close: 'm6 6 12 12M18 6 6 18',
  camera: 'M4 7h4l2-2h4l2 2h4v12H4zm11 6a3 3 0 1 1-6 0 3 3 0 0 1 6 0Z',
  walk: 'M13 5a2 2 0 1 1 4 0 2 2 0 0 1-4 0Zm-2 15 3-5-2-3m0 0 3-3 3 3 3 1m-9-1-4 2m1 7 1-4',
  mobility: 'M3 12h3l3-7 4 14 3-7h5',
  strength: 'M5 9v6m-2-5v4m4-7v10m0-5h10m2-5v10m2-8v6m2-5v4',
  cycle: 'M9 17a4 4 0 1 1-8 0 4 4 0 0 1 8 0Zm14 0a4 4 0 1 1-8 0 4 4 0 0 1 8 0ZM5 17l5-9 4 9m-3-9H8m7-2h3l1 3',
  rest: 'M20 15.5A8.5 8.5 0 0 1 8.5 4 8.5 8.5 0 1 0 20 15.5Z',
}
const solidPaths: Partial<Record<keyof typeof paths, string>> = {
  home: 'M3 10.7 11.1 4a1.4 1.4 0 0 1 1.8 0l8.1 6.7a1 1 0 0 1-1.2 1.6l-.8-.6v7a1.8 1.8 0 0 1-1.8 1.8h-3v-6h-4.4v6h-3A1.8 1.8 0 0 1 5 18.7v-7l-.8.6A1 1 0 0 1 3 10.7Z',
  period: 'M7 5.5V4a1 1 0 0 1 2 0v1.5h6V4a1 1 0 0 1 2 0v1.5h.5A2.5 2.5 0 0 1 20 8v10a2.5 2.5 0 0 1-2.5 2.5h-11A2.5 2.5 0 0 1 4 18V8a2.5 2.5 0 0 1 2.5-2.5H7Zm-1 4h12v1H6Zm6 2.5c-1.4 1.7-2.4 3-2.4 4.1a2.4 2.4 0 0 0 4.8 0c0-1.1-1-2.4-2.4-4.1Z',
  weight: 'M7.5 4.5h9a4 4 0 0 1 4 4v7a4 4 0 0 1-4 4h-9a4 4 0 0 1-4-4v-7a4 4 0 0 1 4-4ZM7 12h1.7a3.4 3.4 0 0 1 6.6 0H17a5.1 5.1 0 0 0-10 0Zm4.6 1.4 1.4.8 1.8-2.9-1.4-.8Z',
  skin: 'M5.4 20v-4.3a6.4 6.4 0 0 1-1-3.5c0-5 3.4-8.5 8.1-8.5 3.7 0 6.2 2.5 6.2 5.8v.7l2 3.1a.7.7 0 0 1-.6 1h-1.4v2.1c0 1-.8 1.8-1.8 1.8h-2.4V20ZM6 15l.7 1a10.6 10.6 0 0 0 4.9-7.1c1.6 1 3.4 1.6 5.7 1.7l.1-1.2a10 10 0 0 1-6.7-2.7A9.8 9.8 0 0 1 6 15Z',
  me: 'M12 12a4 4 0 1 0 0-8 4 4 0 0 0 0 8ZM4.5 20v-1a7.5 5 0 0 1 15 0v1a1 1 0 0 1-1 1h-13a1 1 0 0 1-1-1Z',
}
defineProps<{ name: keyof typeof paths; active?: boolean }>()
</script>
