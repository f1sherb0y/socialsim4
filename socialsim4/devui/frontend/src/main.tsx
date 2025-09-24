import React from 'react'
import ReactDOM from 'react-dom/client'
import { createBrowserRouter, RouterProvider } from 'react-router-dom'
import App from './App'
import Simulation from './pages/Simulation'
import SimTree from './pages/SimTree'

const router = createBrowserRouter([
  { path: '/', element: <App /> },
  { path: '/sim', element: <Simulation /> },
  { path: '/simtree', element: <SimTree /> },
])

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <RouterProvider router={router} />
  </React.StrictMode>
)

