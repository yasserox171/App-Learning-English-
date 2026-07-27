import React, { useEffect, useState } from 'react';
import { api } from '../api.js';
import { useToast } from '../components/util.jsx';

const LEVELS = ['A1', 'A2', 'B1', 'B2', 'C1'];
const TYPES = ['grammar', 'vocabulary', 'reading'];

const EMPTY = {
  level: 'A2',
  qtype: 'grammar',
  passage: '',
  question: '',
  options: ['', '', ''],
  correct_index: 0,
  is_active: true,
};

export default function PlacementBank() {
  const [rows, setRows] = useState([]);
  const [levelFilter, setLevelFilter] = useState('');
  const [form, setForm] = useState(null); // null = closed, {} = editing/creating
  const [toast, toastNode] = useToast();

  const load = () =>
    api.questions(levelFilter).then(setRows).catch((e) => toast(e.message, true));
  useEffect(() => { load(); }, [levelFilter]);

  const save = async () => {
    try {
      const payload = { ...form, options: form.options.filter((o) => o.trim()) };
      if (form.id) await api.patchQuestion(form.id, payload);
      else await api.createQuestion(payload);
      toast('Question saved');
      setForm(null);
      load();
    } catch (e) {
      toast(e.message, true);
    }
  };

  const remove = async (id) => {
    if (!window.confirm('Delete this question?')) return;
    try {
      await api.deleteQuestion(id);
      toast('Question deleted');
      load();
    } catch (e) {
      toast(e.message, true);
    }
  };

  return (
    <>
      <h1 className="page-title">Placement Question Bank</h1>
      <p className="page-sub">
        Independent 60-80 question bank for the adaptive test — never reused
        from lessons (v2 §4.1.2)
      </p>

      <div className="row" style={{ marginBottom: 14 }}>
        <select
          value={levelFilter}
          onChange={(e) => setLevelFilter(e.target.value)}
          style={{ padding: '8px 12px', borderRadius: 8, border: '1px solid var(--line)' }}
        >
          <option value="">All levels ({rows.length})</option>
          {LEVELS.map((l) => <option key={l}>{l}</option>)}
        </select>
        <div className="spacer" />
        <button className="btn primary" onClick={() => setForm({ ...EMPTY })}>
          + New question
        </button>
      </div>

      <div className="grid cols-2">
        <div className="card" style={{ maxHeight: '70vh', overflowY: 'auto' }}>
          <table className="data">
            <thead>
              <tr><th>Question</th><th>Level</th><th>Type</th><th /></tr>
            </thead>
            <tbody>
              {rows.map((q) => (
                <tr key={q.id} style={{ opacity: q.is_active ? 1 : 0.45 }}>
                  <td>{q.question}</td>
                  <td><span className="badge info">{q.level}</span></td>
                  <td><span className="badge muted">{q.qtype}</span></td>
                  <td>
                    <div className="row">
                      <button className="btn ghost sm" onClick={() => setForm({ ...q })}>
                        Edit
                      </button>
                      <button className="btn bad sm" onClick={() => remove(q.id)}>
                        ✕
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        <div className="card">
          {form ? (
            <>
              <h3 style={{ marginTop: 0 }}>{form.id ? 'Edit' : 'New'} question</h3>
              <div className="row">
                <div className="field" style={{ flex: 1 }}>
                  <label>Level</label>
                  <select value={form.level}
                          onChange={(e) => setForm({ ...form, level: e.target.value })}>
                    {LEVELS.map((l) => <option key={l}>{l}</option>)}
                  </select>
                </div>
                <div className="field" style={{ flex: 1 }}>
                  <label>Type</label>
                  <select value={form.qtype}
                          onChange={(e) => setForm({ ...form, qtype: e.target.value })}>
                    {TYPES.map((t) => <option key={t}>{t}</option>)}
                  </select>
                </div>
              </div>
              {form.qtype === 'reading' && (
                <div className="field">
                  <label>Passage</label>
                  <textarea rows={3} value={form.passage}
                            onChange={(e) => setForm({ ...form, passage: e.target.value })} />
                </div>
              )}
              <div className="field">
                <label>Question</label>
                <textarea rows={2} value={form.question}
                          onChange={(e) => setForm({ ...form, question: e.target.value })} />
              </div>
              <div className="field">
                <label>Options (radio = correct answer)</label>
                {form.options.map((opt, i) => (
                  <div className="row" key={i}>
                    <input type="radio" name="correct"
                           checked={form.correct_index === i}
                           onChange={() => setForm({ ...form, correct_index: i })} />
                    <input style={{ flex: 1 }} value={opt}
                           onChange={(e) => {
                             const options = [...form.options];
                             options[i] = e.target.value;
                             setForm({ ...form, options });
                           }} />
                  </div>
                ))}
                <button className="btn ghost sm" style={{ alignSelf: 'flex-start' }}
                        onClick={() => setForm({ ...form, options: [...form.options, ''] })}>
                  + option
                </button>
              </div>
              <div className="row">
                <label style={{ fontSize: 14 }}>
                  <input type="checkbox" checked={form.is_active}
                         onChange={(e) => setForm({ ...form, is_active: e.target.checked })} />
                  {' '}Active
                </label>
                <div className="spacer" />
                <button className="btn ghost" onClick={() => setForm(null)}>Cancel</button>
                <button className="btn primary" onClick={save}>Save</button>
              </div>
            </>
          ) : (
            <div className="empty">Select a question or create a new one</div>
          )}
        </div>
      </div>
      {toastNode}
    </>
  );
}
