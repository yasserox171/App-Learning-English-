import React, { useEffect, useState } from 'react';
import { api } from '../api.js';
import { fmtDate, useToast } from '../components/util.jsx';

export default function ReviewLessons() {
  const [rows, setRows] = useState([]);
  const [toast, toastNode] = useToast();

  const load = () =>
    api.reviewLessons().then(setRows).catch((e) => toast(e.message, true));
  useEffect(() => { load(); }, []);

  const act = async (id, action) => {
    try {
      await api.actLesson(id, action);
      toast(`Lesson ${action}d`);
      load();
    } catch (e) {
      toast(e.message, true);
    }
  };

  return (
    <>
      <h1 className="page-title">Lesson Review Queue</h1>
      <p className="page-sub">
        Content submitted via the Import API in draft mode — invisible to
        learners until approved (v2 §4.1.3)
      </p>
      <div className="card">
        {rows.length === 0 ? (
          <div className="empty">🎉 Nothing waiting for review</div>
        ) : (
          <table className="data">
            <thead>
              <tr>
                <th>Lesson</th>
                <th>Level</th>
                <th>Unit</th>
                <th>Submitted</th>
                <th />
              </tr>
            </thead>
            <tbody>
              {rows.map((r) => (
                <tr key={r.id}>
                  <td>{r.title}</td>
                  <td><span className="badge info">{r.level}</span></td>
                  <td>{r.unit}</td>
                  <td>{fmtDate(r.created_at)}</td>
                  <td>
                    <div className="row">
                      <button className="btn ok sm" onClick={() => act(r.id, 'approve')}>
                        Approve
                      </button>
                      <button className="btn bad sm" onClick={() => act(r.id, 'reject')}>
                        Reject
                      </button>
                    </div>
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
