import { createRoot } from 'react-dom/client'
import { routes } from '@generouted/react-router'
import { createBrowserRouter, RouterProvider } from 'react-router'
import { TamaguiProvider, createTamagui } from '@tamagui/core'
import { defaultConfig } from '@tamagui/config/v6'
import './styles.css'

const router = createBrowserRouter(routes, { basename: import.meta.env.BASE_URL })
const config = createTamagui(defaultConfig)
createRoot(document.getElementById('root')!).render(<TamaguiProvider config={config} defaultTheme="light"><RouterProvider router={router} /></TamaguiProvider>)
