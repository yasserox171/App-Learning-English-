import React from 'react';
import { Navigate, NavLink, Route, Routes, useNavigate } from 'react-router-dom';
import { clearSession, getAdmin, getToken } from './api.js';
import Login from './pages/Login.jsx';
import Dashboard from './pages/Dashboard.jsx';
import ContentTree from './pages/ContentTree.jsx';
import PlacementBank from './pages/PlacementBank.jsx';
import ReviewLessons from './pages/ReviewLessons.jsx';
import ReviewArticles from './pages/ReviewArticles.jsx';
import Users from './pages/Users.jsx';
import Team from './pages/Team.jsx';

// Role → visible sections. The backend enforces this on every endpoint; the
// sidebar just avoids dead links (v2 §4.2).
const CAN = {
  content: ['super', 'content'],
  support: ['super', 'support'],
  superOnly: ['super'],
};

function Shell({ children }) {
  const admin = getAdmin();
  const navigate = useNavigate();
  const role = admin?.role;

  const logout = () => {
    clearSession();
    navigate('/login');
  };

  return (
    <div className="shell">
      <aside className="sidebar">
        <div className="logo">
          Focus<span>Languages</span> · Admin
        </div>
        <nav className="nav">
          <NavLink to="/" end>📊 Dashboard</NavLink>

          {CAN.content.includes(role) && (
            <>
              <div className="group">Content</div>
              <NavLink to="/content">🌳 Content Tree</NavLink>
              <NavLink to="/review/lessons">📥 Lesson Review</NavLink>
              <NavLink to="/review/articles">📰 Article Review</NavLink>
              <NavLink to="/placement">🎯 Placement Bank</NavLink>
            </>
          )}
          {CAN.support.includes(role) && (
            <>
              <div className="group">Users</div>
              <NavLink to="/users">👥 Users & Subscriptions</NavLink>
            </>
          )}
          {CAN.superOnly.includes(role) && (
            <>
              <div className="group">Administration</div>
              <NavLink to="/team">🔐 Team & API Keys</NavLink>
            </>
          )}
        </nav>
        <div className="whoami">
          <div className="role">{role} admin</div>
          <div>{admin?.email}</div>
          <button onClick={logout}>Sign out</button>
        </div>
      </aside>
      <main className="main">{children}</main>
    </div>
  );
}

function Protected({ children }) {
  if (!getToken()) return <Navigate to="/login" replace />;
  return <Shell>{children}</Shell>;
}

export default function App() {
  return (
    <Routes>
      <Route path="/login" element={<Login />} />
      <Route path="/" element={<Protected><Dashboard /></Protected>} />
      <Route path="/content" element={<Protected><ContentTree /></Protected>} />
      <Route path="/review/lessons" element={<Protected><ReviewLessons /></Protected>} />
      <Route path="/review/articles" element={<Protected><ReviewArticles /></Protected>} />
      <Route path="/placement" element={<Protected><PlacementBank /></Protected>} />
      <Route path="/users" element={<Protected><Users /></Protected>} />
      <Route path="/team" element={<Protected><Team /></Protected>} />
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}
