import React, { lazy, Suspense } from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import './App.css';
import ShopSphere from './components/ShopSphere';
import Login from './components/Login';

const Dashboard = lazy(() => import('./components/Dashboard'));

function AdminRoute() {
  let user = null;
  try { user = JSON.parse(localStorage.getItem('currentUser') || 'null'); } catch { /* stale demo data */ }
  return user?.role === 'admin' && localStorage.getItem('adminToken')
    ? <Suspense fallback={<div className="admin-loading">Loading AutoSRE console…</div>}><Dashboard /></Suspense>
    : <Navigate to="/login" replace />;
}

function App() {
  return (
    <Router>
      <div className="app-container">
        <Routes>
          {/* Authentication */}
          <Route path="/login" element={<Login />} />
          
          {/* Public Organization Website */}
          <Route path="/" element={<ShopSphere />} />
          <Route path="/products" element={<ShopSphere />} />
          <Route path="/product/:id" element={<ShopSphere />} />
          <Route path="/cart" element={<ShopSphere />} />
          <Route path="/checkout" element={<ShopSphere />} />
          <Route path="/orders" element={<ShopSphere />} />
          <Route path="/profile" element={<ShopSphere />} />
          
          {/* Internal SRE / Admin Dashboard */}
          <Route path="/dashboard/*" element={<AdminRoute />} />
          <Route path="/incidents/*" element={<AdminRoute />} />
          <Route path="/alerts" element={<AdminRoute />} />
          <Route path="/logs" element={<AdminRoute />} />
          <Route path="/metrics" element={<AdminRoute />} />
          <Route path="/services" element={<AdminRoute />} />
          <Route path="/agents" element={<AdminRoute />} />
          <Route path="/history" element={<AdminRoute />} />
          <Route path="/admin" element={<Navigate to="/dashboard" replace />} />
        </Routes>
      </div>
    </Router>
  );
}

export default App;
