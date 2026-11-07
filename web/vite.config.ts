import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import generouted from '@generouted/react-router/plugin'
import tailwindcss from '@tailwindcss/vite'

export default defineConfig({ plugins: [react(), generouted(), tailwindcss()] })
