import { defineConfig } from 'vite'
import uni from '@dcloudio/vite-plugin-uni'

// H5 直连后端：.env.development.local 写 VITE_API_BASE_URL=http://127.0.0.1:8000
export default defineConfig({
  plugins: [uni()],
  server: {
    host: '127.0.0.1',
    port: 5173
  }
})
