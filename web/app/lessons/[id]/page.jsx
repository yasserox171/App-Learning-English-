'use client';

import Link from 'next/link';
import { useEffect, useState } from 'react';
import { useParams } from 'next/navigation';
import { api } from '../../../lib/api';
import { useSession } from '../../../components/SessionProvider';

const escapeRe = (s) => s.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');

/**
 * Lesson reader. Terms above the lesson's own CEFR level are the only ones
 * marked tappable — tap to reveal the Arabic translation (v2 §1.1).
 * Multi-word entries (idioms, "boarding pass") are matched longest-first so a
 * fixed expression reveals as one unit rather than word by word.
 */
function SelectiveText({ text, annotations }) {
  const [revealed, setRevealed] = useState({});

  const lookup = new Map(
    (annotations || [])
      .filter((a) => a.word?.trim())
      .map((a) => [a.word.toLowerCase(), a])
  );

  const source = String(text);
  const terms = [...lookup.keys()].sort((a, b) => b.length - a.length);
  if (terms.length === 0) {
    return (
      <p dir="ltr" style={{ textAlign: 'start', whiteSpace: 'pre-wrap' }}>
        {source}
      </p>
    );
  }

  const pattern = new RegExp(`\\b(?:${terms.map(escapeRe).join('|')})\\b`, 'gi');
  const nodes = [];
  let cursor = 0;
  let occurrence = 0;

  for (const match of source.matchAll(pattern)) {
    if (match.index > cursor) {
      nodes.push(<span key={`t${cursor}`}>{source.slice(cursor, match.index)}</span>);
    }
    cursor = match.index + match[0].length;

    const hit = lookup.get(match[0].toLowerCase());
    if (!hit) {
      nodes.push(<span key={`p${cursor}`}>{match[0]}</span>);
      continue;
    }
    const index = occurrence++;
    nodes.push(
      <span key={`a${index}`}>
        <button
          onClick={() => setRevealed((prev) => ({ ...prev, [index]: !prev[index] }))}
          style={{
            border: 'none',
            background: 'none',
            padding: 0,
            font: 'inherit',
            color: 'inherit',
            borderBottom: '1.5px dotted var(--brand)',
          }}
        >
          {match[0]}
        </button>
        {revealed[index] && (
          <span dir="rtl" style={{ color: 'var(--brand)', fontWeight: 600 }}>
            {' '}
            ({hit.translation_ar})
          </span>
        )}
      </span>
    );
  }
  if (cursor < source.length) {
    nodes.push(<span key="tail">{source.slice(cursor)}</span>);
  }

  return (
    <p dir="ltr" style={{ textAlign: 'start', whiteSpace: 'pre-wrap' }}>
      {nodes}
    </p>
  );
}

export default function LessonPage() {
  const { id } = useParams();
  const { loading: sessionLoading } = useSession();
  const [lesson, setLesson] = useState(null);
  const [denied, setDenied] = useState(false);

  useEffect(() => {
    if (sessionLoading) return;
    api
      .lesson(id)
      .then(setLesson)
      .catch((err) => (err.status === 403 ? setDenied(true) : setLesson(false)));
  }, [id, sessionLoading]);

  if (denied)
    return (
      <div className="empty">
        هذا الدرس متاح للمشتركين.{' '}
        <Link href="/premium" className="badge">
          اشترك الآن
        </Link>
      </div>
    );
  if (lesson === false) return <div className="empty">تعذّر تحميل الدرس.</div>;
  if (!lesson) return <div className="spinner" />;

  return (
    <>
      <h1 className="page" dir="ltr" style={{ textAlign: 'start' }}>
        {lesson.title}
      </h1>
      <p className="sub">{lesson.description}</p>

      <Link href={`/tutor/${id}`} className="btn primary" style={{ display: 'inline-block' }}>
        🎙️ تحدّث مع المدرّس الذكي
      </Link>

      {(lesson.components || []).map((component) => (
        <div className="card" key={component.id}>
          {component.type === 'text' && (
            <SelectiveText
              text={component.payload?.content || ''}
              annotations={lesson.annotations}
            />
          )}

          {component.type === 'vocabulary' &&
            (component.payload || []).map((item) => (
              <div key={item.id} className="pay-alt">
                <span dir="ltr">{item.word}</span>
                <strong>{item.translation}</strong>
              </div>
            ))}

          {component.type === 'video' && component.payload?.url && (
            <video controls style={{ width: '100%', borderRadius: 10 }}>
              <source src={component.payload.url} />
            </video>
          )}

          {component.type === 'exercise' &&
            (component.payload || []).map((ex) => (
              <p key={ex.id} dir="ltr" style={{ textAlign: 'start' }}>
                {ex.content?.question ||
                  ex.content?.statement ||
                  ex.content?.sentence}
              </p>
            ))}
        </div>
      ))}
    </>
  );
}
