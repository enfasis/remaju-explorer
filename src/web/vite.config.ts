import { fileURLToPath } from 'node:url'
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import generouted from '@generouted/react-router/plugin'
import tailwindcss from '@tailwindcss/vite'

const tamaguiCopy = (path: string) => fileURLToPath(new URL(`./node_modules/tamagui/node_modules/@tamagui/${path}`, import.meta.url))
const shared = [
  { find: /^@tamagui\/popper$/, replacement: tamaguiCopy('popper') },
  { find: /^@tamagui\/floating$/, replacement: tamaguiCopy('popper/node_modules/@tamagui/floating') },
  { find: /^@tamagui\/portal$/, replacement: tamaguiCopy('portal') },
]

export default defineConfig({
  base: process.env.VITE_BASE_PATH || '/',
  server: { allowedHosts: ['web'] },
  define: { 'process.env': '{}' },
  resolve: { alias: shared },
  optimizeDeps: {
    include: ['leaflet', 'nuqs', 'nuqs/adapters/react-router/v7', 'tamagui', '@tamagui/config/v6-base', '@tamagui/config/v6-builder', '@tamagui/config/animations-css'],
    esbuildOptions: { define: { 'process.env': '{}' } },
  },
  plugins: [react(), generouted(), tailwindcss()],
})
