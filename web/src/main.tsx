import { createRoot } from 'react-dom/client'
import { routes } from '@generouted/react-router'
import { createBrowserRouter, RouterProvider } from 'react-router'
import './styles.css'

const router = createBrowserRouter(routes, { basename: import.meta.env.BASE_URL })
createRoot(document.getElementById('root')!).render(<RouterProvider router={router} />)
