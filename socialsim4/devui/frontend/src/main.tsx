import React from 'react'
import ReactDOM from 'react-dom/client'
import { createBrowserRouter, RouterProvider } from 'react-router-dom'
import App from './App'
import Simulation from './pages/Simulation'
import SimTree from './pages/SimTree'
import Studio from './pages/Studio'
import './styles/radix-theme.css'

const router = createBrowserRouter([
  { path: '/', element: <App /> },
  { path: '/sim/:treeId?', element: <Simulation /> },
  { path: '/simtree', element: <SimTree /> },
  { path: '/simtree/:treeId', element: <SimTree /> },
  { path: '/studio', element: <Studio /> },
  { path: '/studio/:treeId', element: <Studio /> },
])

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <RouterProvider router={router} />
  </React.StrictMode>
)
