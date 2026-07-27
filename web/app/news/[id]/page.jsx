'use client';

import { useEffect, useState } from 'react';
import { useParams } from 'next/navigation';
import { api } from '../../../lib/api';
import { useSession } from '../../../components/SessionProvider';

/** Reading + comprehension questions. Coins are awarded server-side only. */
export default function ArticlePage() {
  const { id } = useParams();
  const { loading: sessionLoading, refreshWallet } = useSession();
  const [article, setArticle] = useState(null);
  const [results, setResults] = useState({}); // exerciseId → server result
  const [picked, setPicked] = useState({}); // exerciseId → chosen option index
  const [toast, setToast] = useState('');

  useEffect(() => {
    if (sessionLoading) return;
    api.article(id).then(setArticle).catch(() => setArticle(false));
  }, [id, sessionLoading]);

  const answer = async (exercise, payload) => {
    if (results[exercise.id]) return;
    try {
      const result = await api.submitAnswer(id, exercise.id, payload);
      setResults((prev) => ({ ...prev, [exercise.id]: result }));
      const earned = (result.coins_awarded || 0) + (result.bonus_awarded || 0);
      if (earned > 0) {
        setToast(
          result.bonus_awarded
            ? `🪙 +${earned} عملة — مكافأة الإكمال!`
            : `🪙 +${earned} عملة`
        );
        refreshWallet();
      } else if (result.cap_reached) {
        setToast('وصلت للحد اليومي — عد غداً! 🌙');
      }
      setTimeout(() => setToast(''), 2500);
    } catch {
      setToast('تعذّر إرسال الإجابة');
    }
  };

  if (article === false) return <div className="empty">تعذّر تحميل المقال.</div>;
  if (!article) return <div className="spinner" />;

  return (
    <>
      <h1 className="page" dir="ltr" style={{ textAlign: 'start' }}>
        {article.title_en}
      </h1>
      <p className="sub">
        {article.title_ar} · <span className="badge">{article.difficulty}</span>
      </p>

      <article className="card" dir="ltr" style={{ textAlign: 'start' }}>
        <p style={{ whiteSpace: 'pre-wrap' }}>
          {article.body || article.content_short}
        </p>
      </article>

      <h2 style={{ fontSize: 20 }}>أسئلة الفهم</h2>
      {(article.exercises || []).map((ex) => {
        const result = results[ex.id];
        const content = ex.content || {};
        return (
          <div className="card" key={ex.id}>
            <p dir="ltr" style={{ textAlign: 'start', fontWeight: 600 }}>
              {content.question || content.statement || content.sentence}
            </p>

            {ex.template === 'multiple_choice' &&
              (content.options || []).map((opt, i) => {
                let state = '';
                if (result && picked[ex.id] === i) {
                  state = result.is_correct ? ' correct' : ' wrong';
                }
                return (
                  <button
                    key={i}
                    className={`option${state}`}
                    dir="ltr"
                    disabled={!!result}
                    onClick={() => {
                      setPicked((prev) => ({ ...prev, [ex.id]: i }));
                      answer(ex, { selected_index: i });
                    }}
                  >
                    {opt}
                  </button>
                );
              })}

            {ex.template === 'true_false' &&
              [true, false].map((value) => (
                <button
                  key={String(value)}
                  className="option"
                  disabled={!!result}
                  onClick={() => answer(ex, { answer: value })}
                >
                  {value ? '✔ صحيح' : '✘ خطأ'}
                </button>
              ))}

            {ex.template === 'fill_blank' && !result && (
              <form
                onSubmit={(e) => {
                  e.preventDefault();
                  answer(ex, { answer: e.target.elements.blank.value });
                }}
              >
                <input
                  name="blank"
                  dir="ltr"
                  className="option"
                  placeholder="اكتب الإجابة…"
                  style={{ marginBottom: 10 }}
                />
                <button className="btn primary">تحقّق</button>
              </form>
            )}

            {result && (
              <p className={`badge ${result.is_correct ? 'ok' : 'bad'}`}>
                {result.is_correct
                  ? '✓ إجابة صحيحة'
                  : `✘ الإجابة الصحيحة: ${result.correct_answer}`}
              </p>
            )}
          </div>
        );
      })}

      {toast && (
        <div
          className="card"
          style={{
            position: 'fixed',
            bottom: 24,
            insetInlineStart: 24,
            margin: 0,
            padding: '12px 18px',
          }}
        >
          {toast}
        </div>
      )}
    </>
  );
}
