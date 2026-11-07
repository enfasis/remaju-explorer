import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import generouted from '@generouted/react-router/plugin'
import tailwindcss from '@tailwindcss/vite'

export default defineConfig({ base: process.env.VITE_BASE_PATH || '/', define: { 'process.env': '{}' }, optimizeDeps: { include: ['leaflet', 'nuqs', 'nuqs/adapters/react-router/v7', '@tamagui/button'], esbuildOptions: { define: { 'process.env': '{}' } } }, plugins: [react(), generouted(), tailwindcss()] })
