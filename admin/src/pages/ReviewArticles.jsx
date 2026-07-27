import React, { useEffect, useState } from 'react';
import { api } from '../api.js';
import { useToast } from '../components/util.jsx';

const LEVELS = ['', 'A1', 'A2', 'B1', 'B2', 'C1'];

export default function ReviewArticles() {
  const [rows, setRows] = useState([]);
  const [filters, setFilters] = useState({ category: '', country: '', level: '' });
  const [editing, setEditing] = useState(null); // article being edited
  const [toast, toastNode] = useToast();

  const load = () =>
    api.reviewArticles(filters).then(setRows).catch((e) => toast(e.message, true));
  useEffect(() => { load(); }, [filters]);

  const act = async (id, action) => {
    try {
      await api.actArticle(id, action);
      toast(`Article ${action}d`);
      setEditing(null);
      load();
    } catch (e) {
      toast(e.message, true);
    }
  };

  const saveEdit = async () => {
    try {
      await api.patchArticle(editing.id, {
        title_en: editing.title_en,
        title_ar: editing.title_ar,
        content_short: editing.content_short,
        body: editing.body,
      });
      toast('Article updated');
      load();
    } catch (e) {
      toast(e.message, true);
    }
  };

  return (
    <>
      <h1 className="page-title">Article & Story Review</h1>
      <p className="page-sub">
        AI-generated content pending review before publish — filterable by
        category, country and level (v2 §4.1.4)
      </p>

      <div className="row" style={{ marginBottom: 14 }}>
        <input
          placeholder="Category code…"
          value={filters.category}
          onChange={(e) => setFilters({ ...filters, category: e.target.value })}
          style={{ padding: '8px 12px', borderRadius: 8, border: '1px solid var(--line)' }}
        />
        <input
          placeholder="Country (ma, eg…)"
          value={filters.country}
          onChange={(e) => setFilters({ ...filters, country: e.target.value })}
          style={{ padding: '8px 12px', borderRadius: 8, border: '1px solid var(--line)', width: 140 }}
        />
        <select
          value={filters.level}
          onChange={(e) => setFilters({ ...filters, level: e.target.value })}
          style={{ padding: '8px 12px', borderRadius: 8, border: '1px solid var(--line)' }}
        >
          {LEVELS.map((l) => (
            <option key={l} value={l}>{l || 'All levels'}</option>
          ))}
        </select>
      </div>

      <div className="grid cols-2">
        <div className="card">
          {rows.length === 0 ? (
            <div className="empty">🎉 Review queue is empty</div>
          ) : (
            <table className="data">
              <thead>
                <tr><th>Article</th><th>Type</th><th>Level</th><th /></tr>
              </thead>
              <tbody>
                {rows.map((a) => (
                  <tr key={a.id}>
                    <td>
                      <div style={{ fontWeight: 600 }}>{a.title_en}</div>
                      <div style={{ color: 'var(--ink-soft)', fontSize: 12 }}>
                        {a.category?.code || '—'} · {a.country}
                        {a.is_global ? ' · global' : ''}
                      </div>
                    </td>
                    <td>
                      <span className={`badge ${a.content_type === 'story' ? 'info' : 'muted'}`}>
                        {a.content_type}
                      </span>
                    </td>
                    <td><span className="badge info">{a.difficulty}</span></td>
                    <td>
                      <button className="btn ghost sm" onClick={() => setEditing({ ...a })}>
                        Open
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>

        <div className="card">
          {editing ? (
            <>
              <div className="field">
                <label>Title (EN)</label>
                <input
                  value={editing.title_en}
                  onChange={(e) => setEditing({ ...editing, title_en: e.target.value })}
                />
              </div>
              <div className="field">
                <label>Title (AR)</label>
                <input
                  dir="rtl"
                  value={editing.title_ar}
                  onChange={(e) => setEditing({ ...editing, title_ar: e.target.value })}
                />
              </div>
              <div className="field">
                <label>Summary</label>
                <textarea
                  rows={2}
                  value={editing.content_short}
                  onChange={(e) => setEditing({ ...editing, content_short: e.target.value })}
                />
              </div>
              <div className="field">
                <label>Body (fully rewritten — never source text)</label>
                <textarea
                  rows={9}
                  value={editing.body}
                  onChange={(e) => setEditing({ ...editing, body: e.target.value })}
                />
              </div>
              {(editing.exercises || []).length > 0 && (
                <div className="field">
                  <label>Comprehension questions ({editing.exercises.length})</label>
                  {editing.exercises.map((ex) => (
                    <div className="pv-exercise" key={ex.id}>
                      <div className="tpl">{ex.template}</div>
                      {ex.content?.question || ex.content?.statement || ex.content?.sentence}
                    </div>
                  ))}
                </div>
              )}
              <div className="row">
                <button className="btn ghost" onClick={saveEdit}>Save edits</button>
                <div className="spacer" />
                <button className="btn ok" onClick={() => act(editing.id, 'approve')}>
                  ✓ Publish
                </button>
                <button className="btn bad" onClick={() => act(editing.id, 'reject')}>
                  ✕ Reject
                </button>
              </div>
            </>
          ) : (
            <div className="empty">Open an article to review it</div>
          )}
        </div>
      </div>
      {toastNode}
    </>
  );
}
