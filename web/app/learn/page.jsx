'use client';

import Link from 'next/link';
import { useEffect, useState } from 'react';
import { api } from '../../lib/api';
import { useSession } from '../../components/SessionProvider';

export default function LearnPage() {
  const { loading: sessionLoading } = useSession();
  const [levels, setLevels] = useState(null);
  const [openLevel, setOpenLevel] = useState(null);
  const [units, setUnits] = useState({});
  const [lessons, setLessons] = useState({});

  useEffect(() => {
    if (sessionLoading) return;
    api
      .levels()
      .then((data) => setLevels(data.results || data))
      .catch(() => setLevels([]));
  }, [sessionLoading]);

  const toggleLevel = async (level) => {
    const next = openLevel === level.id ? null : level.id;
    setOpenLevel(next);
    if (next && !units[level.id]) {
      const data = await api.levelUnits(level.id);
      setUnits((prev) => ({ ...prev, [level.id]: data.results || data }));
    }
  };

  const loadLessons = async (unit) => {
    if (lessons[unit.id]) return;
    const data = await api.unitLessons(unit.id);
    setLessons((prev) => ({ ...prev, [unit.id]: data.results || data }));
  };

  if (!levels) return <div className="spinner" />;

  return (
    <>
      <h1 className="page">📚 الدروس</h1>
      <p className="sub">من A1 إلى C2 — اختر مستواك وابدأ.</p>

      {levels.map((level) => (
        <div className="card" key={level.id}>
          <button
            className="btn ghost"
            style={{ width: '100%', textAlign: 'start' }}
            onClick={() => toggleLevel(level)}
          >
            <strong>{level.code}</strong> — {level.name}
          </button>

          {openLevel === level.id &&
            (units[level.id] || []).map((unit) => (
              <details
                key={unit.id}
                style={{ marginTop: 10 }}
                onToggle={(e) => e.target.open && loadLessons(unit)}
              >
                <summary style={{ cursor: 'pointer' }}>{unit.title}</summary>
                <ul style={{ paddingInlineStart: 20 }}>
                  {(lessons[unit.id] || []).map((lesson) => (
                    <li key={lesson.id} style={{ marginBottom: 6 }}>
                      <Link href={`/lessons/${lesson.id}`}>{lesson.title}</Link>
                    </li>
                  ))}
                </ul>
              </details>
            ))}
        </div>
      ))}
    </>
  );
}
