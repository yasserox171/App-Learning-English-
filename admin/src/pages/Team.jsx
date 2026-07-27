import React, { useEffect, useState } from 'react';
import { api } from '../api.js';
import { fmtDate, useToast } from '../components/util.jsx';

export default function Team() {
  const [admins, setAdmins] = useState([]);
  const [keys, setKeys] = useState([]);
  const [logs, setLogs] = useState([]);
  const [newAdmin, setNewAdmin] = useState({ email: '', password: '', full_name: '', role: 'content' });
  const [newKey, setNewKey] = useState({ name: '', trust_level: 'draft_only' });
  const [mintedKey, setMintedKey] = useState(null);
  const [toast, toastNode] = useToast();

  const load = () => {
    api.admins().then(setAdmins).catch((e) => toast(e.message, true));
    api.apiKeys().then(setKeys).catch(() => {});
    api.importLogs().then(setLogs).catch(() => {});
  };
  useEffect(() => { load(); }, []);

  const createAdmin = async () => {
    try {
      await api.createAdmin(newAdmin);
      toast('Admin created');
      setNewAdmin({ email: '', password: '', full_name: '', role: 'content' });
      load();
    } catch (e) {
      toast(e.message, true);
    }
  };

  const toggleAdmin = async (a) => {
    try {
      await api.patchAdmin(a.id, { is_active: !a.is_active });
      load();
    } catch (e) {
      toast(e.message, true);
    }
  };

  const createKey = async () => {
    try {
      const resp = await api.createApiKey(newKey);
      setMintedKey(resp.key);
      setNewKey({ name: '', trust_level: 'draft_only' });
      load();
    } catch (e) {
      toast(e.message, true);
    }
  };

  const revoke = async (id) => {
    if (!window.confirm('Revoke this API key? Pipelines using it will stop working.')) return;
    try {
      await api.revokeApiKey(id);
      toast('Key revoked');
      load();
    } catch (e) {
      toast(e.message, true);
    }
  };

  return (
    <>
      <h1 className="page-title">Team & API Keys</h1>
      <p className="page-sub">
        Super Admin only — admin accounts, import API keys with trust tiers,
        and the direct-publish audit trail (v2 §4.2 / §5.1)
      </p>

      <div className="grid cols-2" style={{ marginBottom: 16 }}>
        <div className="card">
          <h3 style={{ marginTop: 0 }}>Admin accounts</h3>
          <table className="data">
            <thead><tr><th>Email</th><th>Role</th><th>Status</th><th /></tr></thead>
            <tbody>
              {admins.map((a) => (
                <tr key={a.id}>
                  <td>{a.email}<div style={{ fontSize: 12, color: 'var(--ink-soft)' }}>{a.full_name}</div></td>
                  <td><span className="badge info">{a.role}</span></td>
                  <td><span className={`badge ${a.is_active ? 'ok' : 'bad'}`}>{a.is_active ? 'active' : 'disabled'}</span></td>
                  <td>
                    <button className="btn ghost sm" onClick={() => toggleAdmin(a)}>
                      {a.is_active ? 'Disable' : 'Enable'}
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
          <h4>Add admin</h4>
          <div className="row">
            <input placeholder="email" value={newAdmin.email}
                   onChange={(e) => setNewAdmin({ ...newAdmin, email: e.target.value })}
                   style={{ flex: 1, padding: 8, borderRadius: 8, border: '1px solid var(--line)' }} />
            <input placeholder="password (8+)" type="password" value={newAdmin.password}
                   onChange={(e) => setNewAdmin({ ...newAdmin, password: e.target.value })}
                   style={{ width: 140, padding: 8, borderRadius: 8, border: '1px solid var(--line)' }} />
            <select value={newAdmin.role}
                    onChange={(e) => setNewAdmin({ ...newAdmin, role: e.target.value })}
                    style={{ padding: 8, borderRadius: 8, border: '1px solid var(--line)' }}>
              <option value="super">super</option>
              <option value="content">content</option>
              <option value="support">support</option>
            </select>
            <button className="btn primary sm" onClick={createAdmin}>Add</button>
          </div>
        </div>

        <div className="card">
          <h3 style={{ marginTop: 0 }}>Import API keys</h3>
          {mintedKey && (
            <>
              <div className="badge warn">Copy now — shown only once</div>
              <div className="keybox">{mintedKey}</div>
            </>
          )}
          <table className="data">
            <thead><tr><th>Name</th><th>Trust</th><th>Last used</th><th /></tr></thead>
            <tbody>
              {keys.map((k) => (
                <tr key={k.id} style={{ opacity: k.is_active ? 1 : 0.4 }}>
                  <td>{k.name}<div className="mono">{k.prefix}…</div></td>
                  <td>
                    <span className={`badge ${k.trust_level === 'direct_publish' ? 'warn' : 'muted'}`}>
                      {k.trust_level}
                    </span>
                  </td>
                  <td style={{ fontSize: 12 }}>{fmtDate(k.last_used_at)}</td>
                  <td>
                    {k.is_active && (
                      <button className="btn bad sm" onClick={() => revoke(k.id)}>Revoke</button>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
          <h4>Generate key</h4>
          <div className="row">
            <input placeholder="key name (e.g. content-pipeline)" value={newKey.name}
                   onChange={(e) => setNewKey({ ...newKey, name: e.target.value })}
                   style={{ flex: 1, padding: 8, borderRadius: 8, border: '1px solid var(--line)' }} />
            <select value={newKey.trust_level}
                    onChange={(e) => setNewKey({ ...newKey, trust_level: e.target.value })}
                    style={{ padding: 8, borderRadius: 8, border: '1px solid var(--line)' }}>
              <option value="draft_only">draft_only</option>
              <option value="direct_publish">direct_publish</option>
            </select>
            <button className="btn primary sm" onClick={createKey}>Generate</button>
          </div>
        </div>
      </div>

      <div className="card">
        <h3 style={{ marginTop: 0 }}>Import log (latest 200)</h3>
        {logs.length === 0 ? (
          <div className="empty">No imports yet</div>
        ) : (
          <table className="data">
            <thead>
              <tr><th>When</th><th>Key</th><th>Mode</th><th>Content</th><th>Result</th></tr>
            </thead>
            <tbody>
              {logs.map((l) => (
                <tr key={l.id}>
                  <td style={{ fontSize: 12 }}>{fmtDate(l.created_at)}</td>
                  <td>{l.api_key || '—'}</td>
                  <td>
                    <span className={`badge ${l.publish_mode === 'direct' ? 'warn' : 'muted'}`}>
                      {l.publish_mode}
                    </span>
                  </td>
                  <td>
                    {l.content_title || '—'}
                    {l.content_id && <div className="mono">{l.content_id}</div>}
                  </td>
                  <td>
                    <span className={`badge ${l.success ? 'ok' : 'bad'}`}>
                      {l.success ? 'ok' : 'failed'}
                    </span>
                    {l.detail && <div style={{ fontSize: 12 }}>{l.detail}</div>}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
      {toastNode}
    </>
  );
}
