import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import generouted from '@generouted/react-router/plugin'
import tailwindcss from '@tailwindcss/vite'

export default defineConfig({ base: process.env.VITE_BASE_PATH || '/', plugins: [react(), generouted(), tailwindcss()] })
