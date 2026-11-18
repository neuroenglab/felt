import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react-swc'
import path from 'node:path'
import { fileURLToPath } from 'node:url'

const dirname = path.dirname(fileURLToPath(import.meta.url))

const basePath = process.env.VITE_BASE_PATH ?? '/'
const normalizedBasePath = basePath.endsWith('/') ? basePath : `${basePath}/`

// https://vite.dev/config/
export default defineConfig({
  base: normalizedBasePath,
  plugins: [react()],
  build: {
    // The Python package serves the page from here, so the wheel carries it.
    outDir: path.resolve(dirname, '../src/felt/static'),
    emptyOutDir: true,
  },
  resolve: {
    alias: {
      // Use the vendored feedback-locator source instead of the published
      // npm package, so component edits hot-reload without a publish cycle.
      '@neuroenglab/nel-feedback-ui': path.resolve(
        dirname,
        'feedback-locator/src/index.ts',
      ),
    },
  },
  server: {
    proxy: {
      '/api': 'http://127.0.0.1:5000',
    },
  },
})
