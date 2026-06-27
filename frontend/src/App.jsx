import React from 'react';
import { BrowserRouter, Routes, Route, NavLink, Navigate } from 'react-router-dom';
import HomePage       from './pages/HomePage';
import TrackingPage   from './pages/TrackingPage';
import StaticCalcPage from './pages/StaticCalcPage';
import ComparisonPage from './pages/ComparisonPage';
import StatusBar      from './components/ui/StatusBar';
import './index.css';
import 'leaflet/dist/leaflet.css';

// Fix Leaflet default marker icon path (Vite bundler issue)
import L from 'leaflet';
import markerIcon2x   from 'leaflet/dist/images/marker-icon-2x.png';
import markerIcon     from 'leaflet/dist/images/marker-icon.png';
import markerShadow   from 'leaflet/dist/images/marker-shadow.png';
delete L.Icon.Default.prototype._getIconUrl;
L.Icon.Default.mergeOptions({ iconUrl: markerIcon, iconRetinaUrl: markerIcon2x, shadowUrl: markerShadow });

export default function App() {
  return (
    <BrowserRouter>
      <div className="app-layout">
        {/* ── Top navigation bar ── */}
        <nav className="navbar">
          <NavLink to="/" className="navbar-brand">
            <span>🛰️ TargetTrack</span>
            <span className="brand-badge">v2.0</span>
          </NavLink>

          <div className="navbar-links">
            <NavLink to="/"           className={({ isActive }) => `nav-link${isActive ? ' active' : ''}`} end>🏠 Dashboard</NavLink>
            <NavLink to="/tracking"   className={({ isActive }) => `nav-link${isActive ? ' active' : ''}`}>📡 Live Tracking</NavLink>
            <NavLink to="/calculator" className={({ isActive }) => `nav-link${isActive ? ' active' : ''}`}>📐 Calculator</NavLink>
            <NavLink to="/comparison" className={({ isActive }) => `nav-link${isActive ? ' active' : ''}`}>📊 So sánh</NavLink>
          </div>

          <div className="navbar-status">
            <StatusBar />
          </div>
        </nav>

        {/* ── Page area ── */}
        <main className="page-content">
          <Routes>
            <Route path="/"           element={<HomePage />} />
            <Route path="/tracking"   element={<TrackingPage />} />
            <Route path="/calculator" element={<StaticCalcPage />} />
            <Route path="/comparison" element={<ComparisonPage />} />
            <Route path="*"           element={<Navigate to="/" replace />} />
          </Routes>
        </main>
      </div>
    </BrowserRouter>
  );
}
