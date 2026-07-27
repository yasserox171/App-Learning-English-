import React, { useEffect, useState } from 'react';
import { api } from '../api.js';
import { fmtDate, useToast } from '../components/util.jsx';

export default function Users() {
  const [search, setSearch] = useState('');
  const [data, setData] = useState({ results: [], total: 0, page: 1 });
  const [detail, setDetail] = useState(null);
  const [grant, setGrant] = useState({ plan_type: 'monthly', duration_days: 30 });
  const [toast, toastNode] = useToast();

  const load = (page = 1) =>
    api.users(search, page).then(setData).catch((e) => toast(e.message, true));
  useEffect(() => { load(); }, []);

  const open = (id) =>
    api.userDetail(id).then(setDetail).catch((e) => toast(e.message, true));

  const activate = async () => {
    try {
      const resp = await api.activatePremium({
        email: detail.email,
        plan_type: grant.plan_type,
        duration_days: Number(grant.duration_days),
      });
      toast(`Premium active until ${fmtDate(resp.granted_until)}`);
      setDetail(resp.user);
    } catch (e) {
      toast(e.message, true);
    }
  };

  return (
    <>
      <h1 className="page-title">Users & Subscriptions</h1>
      <p className="page-sub">
        Search by email/name; manual activation for WhatsApp / bank-transfer
        payments (v2 §4.1.5)
      </p>

      <form
        className="row"
        style={{ marginBottom: 14 }}
        onSubmit={(e) => { e.preventDefault(); load(); }}
      >
        <input
          placeholder="Search email or name…"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          style={{ flex: 1, maxWidth: 420, padding: '10px 14px',
                   borderRadius: 8, border: '1px solid var(--line)' }}
        />
        <button className="btn primary">Search</button>
        <span className="badge muted">{data.total} users</span>
      </form>

      <div className="grid cols-2">
        <div className="card" style={{ maxHeight: '70vh', overflowY: 'auto' }}>
          <table className="data">
            <thead>
              <tr><th>User</th><th>Type</th><th>Premium</th><th>Joined</th></tr>
            </thead>
            <tbody>
              {data.results.map((u) => (
                <tr key={u.id} onClick={() => open(u.id)} style={{ cursor: 'pointer' }}>
                  <td>
                    <div style={{ fontWeight: 600 }}>{u.email}</div>
                    <div style={{ fontSize: 12, color: 'var(--ink-soft)' }}>
                      {u.full_name || '—'} {u.country && `· ${u.country.toUpperCase()}`}
                    </div>
                  </td>
                  <td>
                    <span className={`badge ${u.is_guest ? 'muted' : 'info'}`}>
                      {u.is_guest ? 'guest' : 'registered'}
                    </span>
                  </td>
                  <td>
                    <span className={`badge ${u.premium_active ? 'ok' : 'muted'}`}>
                      {u.premium_active ? 'premium' : 'free'}
                    </span>
                  </td>
                  <td style={{ fontSize: 12 }}>{fmtDate(u.created_at)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        <div className="card">
          {detail ? (
            <>
              <h3 style={{ marginTop: 0 }}>{detail.email}</h3>
              <div className="row" style={{ marginBottom: 14 }}>
                <span className={`badge ${detail.premium_active ? 'ok' : 'muted'}`}>
                  {detail.premium_active
                    ? `Premium until ${fmtDate(detail.premium_until)}`
                    : 'No active premium'}
                </span>
                <span className="badge info">🪙 {detail.coin_balance} coins</span>
              </div>

              <h4>Premium grants</h4>
              {detail.grants?.length ? (
                <table className="data">
                  <thead>
                    <tr><th>Source</th><th>From</th><th>Until</th><th /></tr>
                  </thead>
                  <tbody>
                    {detail.grants.map((g) => (
                      <tr key={g.id}>
                        <td>{g.source}</td>
                        <td style={{ fontSize: 12 }}>{fmtDate(g.start_date)}</td>
                        <td style={{ fontSize: 12 }}>{fmtDate(g.end_date)}</td>
                        <td>{g.is_active && <span className="badge ok">active</span>}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              ) : (
                <div className="empty">No grants yet</div>
              )}

              <h4>Manual activation (WhatsApp / bank transfer)</h4>
              <div className="row">
                <select
                  value={grant.plan_type}
                  onChange={(e) => setGrant({ ...grant, plan_type: e.target.value })}
                  style={{ padding: '9px 12px', borderRadius: 8, border: '1px solid var(--line)' }}
                >
                  <option value="monthly">Monthly</option>
                  <option value="annual">Annual</option>
                  <option value="custom">Custom</option>
                </select>
                <input
                  type="number"
                  min={1}
                  value={grant.duration_days}
                  onChange={(e) => setGrant({ ...grant, duration_days: e.target.value })}
                  style={{ width: 90, padding: '9px 12px', borderRadius: 8,
                           border: '1px solid var(--line)' }}
                />
                <span style={{ fontSize: 13, color: 'var(--ink-soft)' }}>days</span>
                <button className="btn ok" onClick={activate}>Activate premium</button>
              </div>
              <p className="page-sub" style={{ marginTop: 10 }}>
                Stacks on top of any remaining premium time — never replaces it.
              </p>
            </>
          ) : (
            <div className="empty">Select a user</div>
          )}
        </div>
      </div>
      {toastNode}
    </>
  );
}
