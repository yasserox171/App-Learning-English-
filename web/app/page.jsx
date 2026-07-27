'use client';

import Link from 'next/link';
import { useEffect, useState } from 'react';
import { api } from '../lib/api';
import { useSession } from '../components/SessionProvider';

export default function FeedPage() {
  const { loading: sessionLoading } = useSession();
  const [articles, setArticles] = useState(null);

  useEffect(() => {
    if (sessionLoading) return;
    api
      .feed()
      .then((data) => setArticles(data.results || data))
      .catch(() => setArticles([]));
  }, [sessionLoading]);

  return (
    <>
      <h1 className="page">📰 اقرأ وتعلّم</h1>
      <p className="sub">
        مقالات وقصص مختارة حسب اهتماماتك ومستواك — أجب عن الأسئلة واربح عملات.
      </p>

      {!articles && <div className="spinner" />}
      {articles?.length === 0 && (
        <div className="empty">لا توجد مقالات متاحة حالياً.</div>
      )}

      <div className="grid two">
        {articles?.map((a) => (
          <Link key={a.id} href={`/news/${a.id}`} className="card article-card">
            <span className="badge">{a.difficulty}</span>{' '}
            {a.content_type === 'story' && <span className="badge">قصة</span>}
            <h3 style={{ marginTop: 10 }}>{a.title_en}</h3>
            <div className="meta">{a.title_ar}</div>
          </Link>
        ))}
      </div>
    </>
  );
}
