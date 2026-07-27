'use client';

import Link from 'next/link';
import { useState } from 'react';
import { api } from '../../lib/api';

/** Optional adaptive placement test (v2 §1.2) — never forced, always exits
 *  to a result screen that offers alternatives to the suggested level. */
export default function PlacementPage() {
  const [round, setRound] = useState(null);
  const [answers, setAnswers] = useState({});
  const [result, setResult] = useState(null);
  const [busy, setBusy] = useState(false);

  const start = async () => {
    setBusy(true);
    try {
      setRound(await api.placementStart());
      setAnswers({});
    } finally {
      setBusy(false);
    }
  };

  const submit = async () => {
    setBusy(true);
    try {
      const data = await api.placementAnswer(round.session_id, answers);
      if (data.completed) {
        setResult(data);
      } else {
        setRound({ ...data, session_id: round.session_id });
        setAnswers({});
      }
    } finally {
      setBusy(false);
    }
  };

  if (result) {
    return (
      <>
        <h1 className="page">🎯 مستواك المقترح</h1>
        <div className="card" style={{ textAlign: 'center' }}>
          <div style={{ fontSize: 54, fontWeight: 800 }}>
            {result.suggested_level}
          </div>
          <p className="sub">
            {result.correct} / {result.total}
          </p>
          <Link href="/learn" className="btn primary big">
            ابدأ من {result.suggested_level}
          </Link>
          <div style={{ marginTop: 10 }}>
            <Link href="/learn" className="btn ghost">
              ابدأ من البداية (A1)
            </Link>
          </div>
          <div style={{ marginTop: 10 }}>
            <Link href="/learn" style={{ color: 'var(--ink-soft)', fontSize: 14 }}>
              اختر مستوى يدوياً
            </Link>
          </div>
        </div>
      </>
    );
  }

  if (!round) {
    return (
      <>
        <h1 className="page">🎯 اختبر مستواك</h1>
        <p className="sub">
          اختبار قصير واختياري تماماً — يمكنك تخطّيه والبدء من أي مستوى.
        </p>
        <div className="card">
          <button className="btn primary big" onClick={start} disabled={busy}>
            {busy ? '…' : 'ابدأ الاختبار'}
          </button>
          <div style={{ marginTop: 10, textAlign: 'center' }}>
            <Link href="/learn" style={{ color: 'var(--ink-soft)', fontSize: 14 }}>
              تخطّي والبدء من A1
            </Link>
          </div>
        </div>
      </>
    );
  }

  const allAnswered = round.questions.every((q) => q.id in answers);

  return (
    <>
      <h1 className="page">
        🎯 المستوى {round.level} · الجولة {round.round}
      </h1>
      {round.questions.map((q) => (
        <div className="card" key={q.id}>
          {q.passage && (
            <p dir="ltr" style={{ textAlign: 'start', color: 'var(--ink-soft)' }}>
              {q.passage}
            </p>
          )}
          <p dir="ltr" style={{ textAlign: 'start', fontWeight: 600 }}>
            {q.question}
          </p>
          {q.options.map((opt, i) => (
            <button
              key={i}
              dir="ltr"
              className={`option${answers[q.id] === i ? ' correct' : ''}`}
              onClick={() => setAnswers((prev) => ({ ...prev, [q.id]: i }))}
            >
              {opt}
            </button>
          ))}
        </div>
      ))}
      <button
        className="btn primary big"
        disabled={!allAnswered || busy}
        onClick={submit}
      >
        {busy ? '…' : 'متابعة'}
      </button>
    </>
  );
}
