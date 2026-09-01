import React, { useState, useEffect } from 'react';
import { BrowserRouter, Routes, Route, NavLink, Navigate } from 'react-router-dom';
import HomePage       from './pages/HomePage';
import DashboardPage  from './pages/DashboardPage';
import TrackingPage   from './pages/TrackingPage';
import StaticCalcPage from './pages/StaticCalcPage';
import ComparisonPage from './pages/ComparisonPage';
import StatusBar      from './components/ui/StatusBar';
import './index.css';
import 'leaflet/dist/leaflet.css';

// Fix Leaflet default marker icon path (Vite bundler issue)
import L from 'leaflet';
import markerIcon2x from 'leaflet/dist/images/marker-icon-2x.png';
import markerIcon   from 'leaflet/dist/images/marker-icon.png';
import markerShadow from 'leaflet/dist/images/marker-shadow.png';
delete L.Icon.Default.prototype._getIconUrl;
L.Icon.Default.mergeOptions({
  iconUrl: markerIcon,
  iconRetinaUrl: markerIcon2x,
  shadowUrl: markerShadow,
});

export default function App() {
  const [theme, setTheme] = useState(() => {
    return localStorage.getItem('theme') || 'dark';
  });

  useEffect(() => {
    document.documentElement.setAttribute('data-theme', theme);
    localStorage.setItem('theme', theme);
  }, [theme]);

  const toggleTheme = () => setTheme(t => (t === 'dark' ? 'light' : 'dark'));

  return (
    <BrowserRouter>
      <div className="app-layout">
        {/* Top navigation bar */}
        <nav className="navbar">
          <NavLink to="/dashboard" className="navbar-brand">
            <span>GPS-TT</span>
            <span className="brand-badge">C2</span>
          </NavLink>

          <div className="navbar-links">
            <NavLink to="/dashboard" className={({ isActive }) => `nav-link${isActive ? ' active' : ''}`}>
              DASH
            </NavLink>
            <NavLink to="/tracking" className={({ isActive }) => `nav-link${isActive ? ' active' : ''}`}>
              TRACK
            </NavLink>
            <NavLink to="/calculator" className={({ isActive }) => `nav-link${isActive ? ' active' : ''}`}>
              CALC
            </NavLink>
            <NavLink to="/comparison" className={({ isActive }) => `nav-link${isActive ? ' active' : ''}`}>
              DELTA
            </NavLink>
            <NavLink to="/sys" className={({ isActive }) => `nav-link${isActive ? ' active' : ''}`}>
              SYS
            </NavLink>
          </div>

          <div className="navbar-status">
            <StatusBar />
            <button
              id="theme-toggle"
              className="theme-toggle-btn"
              onClick={toggleTheme}
              title={theme === 'dark' ? 'Light mode' : 'Dark mode'}
              aria-label="Toggle theme"
            >
              {theme === 'dark' ? 'L' : 'D'}
            </button>
          </div>
        </nav>

        {/* Page area */}
        <main className="page-content">
          <Routes>
            <Route path="/"           element={<Navigate to="/dashboard" replace />} />
            <Route path="/dashboard"  element={<DashboardPage />} />
            <Route path="/tracking"   element={<TrackingPage />} />
            <Route path="/calculator" element={<StaticCalcPage />} />
            <Route path="/comparison" element={<ComparisonPage />} />
            <Route path="/sys"        element={<HomePage />} />
            <Route path="*"           element={<Navigate to="/dashboard" replace />} />
          </Routes>
        </main>
      </div>
    </BrowserRouter>
  );
}
