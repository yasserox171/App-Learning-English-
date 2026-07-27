import React, { useEffect, useState } from 'react';
import { api } from '../api.js';

const SOURCE_LABELS = {
  coins: 'Coins',
  subscription_monthly: 'Google Play / Stripe (monthly)',
  subscription_annual: 'Annual',
  manual_admin: 'WhatsApp / manual',
};

export default function Dashboard() {
  const [stats, setStats] = useState(null);
  const [error, setError] = useState('');

  useEffect(() => {
    api.stats().then(setStats).catch((e) => setError(e.message));
  }, []);

  if (error) return <div className="empty">⚠️ {error}</div>;
  if (!stats) return <div className="empty">Loading…</div>;

  const maxSignups = Math.max(1, ...stats.daily_signups.map((d) => d.count));

  return (
    <>
      <h1 className="page-title">Dashboard</h1>
      <p className="page-sub">Live platform overview (v2 §4.1.6)</p>

      <div className="grid cols-4" style={{ marginBottom: 16 }}>
        <div className="card stat brand">
          <div className="label">Total users</div>
          <div className="value">{stats.users.total}</div>
          <div className="hint">{stats.users.guests} guests</div>
        </div>
        <div className="card stat">
          <div className="label">New this week</div>
          <div className="value">{stats.users.new_this_week}</div>
        </div>
        <div className="card stat">
          <div className="label">Active subscriptions</div>
          <div className="value">{stats.subscriptions.active_total}</div>
        </div>
        <div className="card stat">
          <div className="label">AI Tutor sessions (7d)</div>
          <div className="value">{stats.ai_tutor.sessions_this_week}</div>
          <div className="hint">
            ≈ ${stats.ai_tutor.estimated_weekly_cost_usd} est. cost
          </div>
        </div>
      </div>

      <div className="grid cols-2">
        <div className="card">
          <h3 style={{ marginTop: 0 }}>Daily signups (30 days)</h3>
          {stats.daily_signups.length === 0 ? (
            <div className="empty">No signups yet</div>
          ) : (
            <div className="chart-bars">
              {stats.daily_signups.map((d) => (
                <div
                  key={d.day}
                  className="bar"
                  title={`${d.day}: ${d.count}`}
                  style={{ height: `${(d.count / maxSignups) * 100}%` }}
                />
              ))}
            </div>
          )}
        </div>

        <div className="card">
          <h3 style={{ marginTop: 0 }}>Subscriptions by source</h3>
          <table className="data">
            <tbody>
              {Object.entries(SOURCE_LABELS).map(([key, label]) => (
                <tr key={key}>
                  <td>{label}</td>
                  <td style={{ textAlign: 'right', fontWeight: 700 }}>
                    {stats.subscriptions.by_source[key] || 0}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
          <h3>Content pipeline</h3>
          <div className="row">
            <span className="badge ok">
              {stats.content.lessons_published} lessons live
            </span>
            <span className="badge warn">
              {stats.content.lessons_pending_review} lessons in review
            </span>
            <span className="badge warn">
              {stats.content.articles_pending_review} articles in review
            </span>
          </div>
        </div>
      </div>
    </>
  );
}
