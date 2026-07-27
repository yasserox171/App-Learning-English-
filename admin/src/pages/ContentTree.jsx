import React, { useEffect, useState } from 'react';
import { api } from '../api.js';
import { StatusBadge, useToast } from '../components/util.jsx';

/* Live phone-frame preview of a lesson as the app renders it (v2 §4.1.1). */
function LessonPreview({ lesson }) {
  if (!lesson) {
    return (
      <div className="phone">
        <div className="screen">
          <div className="empty">Select a lesson to preview</div>
        </div>
      </div>
    );
  }
  return (
    <div className="phone">
      <div className="screen">
        <h4>{lesson.title}</h4>
        {(lesson.components || []).map((c) => (
          <div className="pv-block" key={c.id}>
            {c.type === 'text' && (
              <div className="pv-text">{c.payload?.content}</div>
            )}
            {c.type === 'vocabulary' &&
              (c.payload || []).map((v) => (
                <div className="pv-vocab" key={v.id}>
                  {v.image_url ? <img src={v.image_url} alt="" /> : <div className="pv-vocab-img" />}
                  <div>
                    <div>{v.word}</div>
                    <div className="ar">{v.translation}</div>
                  </div>
                </div>
              ))}
            {c.type === 'video' && (
              <div className="pv-video">
                ▶ {c.payload?.title || 'Video'} ·{' '}
                {Math.round((c.payload?.duration || 0) / 60)} min
              </div>
            )}
            {c.type === 'exercise' &&
              (c.payload || []).map((ex) => (
                <div className="pv-exercise" key={ex.id}>
                  <div className="tpl">{ex.template_code || ex.template}</div>
                  {ex.content?.question || ex.content?.statement ||
                    ex.content?.sentence || 'Final test'}
                </div>
              ))}
          </div>
        ))}
        {lesson.annotations?.length > 0 && (
          <div className="pv-block">
            <div className="tpl" style={{ fontSize: 11, color: '#5b6b85' }}>
              Tappable words ({lesson.annotations.length})
            </div>
            <div className="row" style={{ gap: 6 }}>
              {lesson.annotations.slice(0, 12).map((a) => (
                <span key={a.word} className="badge info" title={a.translation_ar}>
                  {a.word}
                </span>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

export default function ContentTree() {
  const [tree, setTree] = useState([]);
  const [selected, setSelected] = useState(null);
  const [lesson, setLesson] = useState(null);
  const [form, setForm] = useState({ title: '', description: '', status: '' });
  const [toast, toastNode] = useToast();

  const load = () => api.contentTree().then(setTree).catch((e) => toast(e.message, true));
  useEffect(() => { load(); }, []);

  const open = async (id) => {
    setSelected(id);
    try {
      const data = await api.lesson(id);
      setLesson(data);
      setForm({
        title: data.title,
        description: data.description || '',
        status: data.status,
      });
    } catch (e) {
      toast(e.message, true);
    }
  };

  const save = async () => {
    try {
      await api.patchLesson(selected, form);
      toast('Lesson saved');
      load();
      open(selected);
    } catch (e) {
      toast(e.message, true);
    }
  };

  return (
    <>
      <h1 className="page-title">Content Tree</h1>
      <p className="page-sub">
        Levels → Units → Lessons with a live preview of how the app renders
        the lesson
      </p>
      <div className="tree-layout">
        <div className="card tree">
          {tree.map((level) => (
            <details className="level" key={level.id} open>
              <summary>
                {level.code} — {level.name}
              </summary>
              {level.units.map((unit) => (
                <details className="unit" key={unit.id}>
                  <summary>{unit.title}</summary>
                  {unit.lessons.map((l) => (
                    <div
                      key={l.id}
                      className={`lesson-row${selected === l.id ? ' active' : ''}`}
                      onClick={() => open(l.id)}
                    >
                      <span style={{ flex: 1 }}>{l.title}</span>
                      <StatusBadge status={l.status} />
                    </div>
                  ))}
                </details>
              ))}
            </details>
          ))}
        </div>

        <div className="card">
          {lesson ? (
            <>
              <h3 style={{ marginTop: 0 }}>Edit lesson</h3>
              <div className="field">
                <label>Title</label>
                <input
                  value={form.title}
                  onChange={(e) => setForm({ ...form, title: e.target.value })}
                />
              </div>
              <div className="field">
                <label>Description</label>
                <textarea
                  rows={3}
                  value={form.description}
                  onChange={(e) =>
                    setForm({ ...form, description: e.target.value })
                  }
                />
              </div>
              <div className="field">
                <label>Status</label>
                <select
                  value={form.status}
                  onChange={(e) => setForm({ ...form, status: e.target.value })}
                >
                  <option value="published">published</option>
                  <option value="draft">draft</option>
                  <option value="rejected">rejected</option>
                </select>
              </div>
              <button className="btn primary" onClick={save}>
                Save changes
              </button>
              <p className="page-sub" style={{ marginTop: 16 }}>
                Component-level editing (text / vocabulary / video / exercise
                payloads) is available through Django Admin; bulk changes go
                through the Import API.
              </p>
            </>
          ) : (
            <div className="empty">Pick a lesson from the tree</div>
          )}
        </div>

        <LessonPreview lesson={lesson} />
      </div>
      {toastNode}
    </>
  );
}
