import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react-swc'

const basePath = process.env.VITE_BASE_PATH ?? '/'
const normalizedBasePath = basePath.endsWith('/') ? basePath : `${basePath}/`

// https://vite.dev/config/
export default defineConfig({
  base: normalizedBasePath,
  plugins: [react()],
  server: {
    proxy: {
      '/api': 'http://127.0.0.1:5000',
    },
  },
})
