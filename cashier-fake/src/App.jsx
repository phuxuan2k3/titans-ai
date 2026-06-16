import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import CreateOrder from './pages/CreateOrder'
import Cashier from './pages/Cashier'

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<CreateOrder />} />
        <Route path="/cashier" element={<Cashier />} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </BrowserRouter>
  )
}
