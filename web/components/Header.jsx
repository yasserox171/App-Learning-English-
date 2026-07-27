'use client';

import Link from 'next/link';
import { useSession } from './SessionProvider';

export default function Header() {
  const { user, wallet } = useSession();

  return (
    <header className="site">
      <div className="inner">
        <Link href="/" className="brand">
          Focus<span>Languages</span>
        </Link>
        <nav>
          <Link href="/">أخبار</Link>
          <Link href="/learn">الدروس</Link>
          <Link href="/placement">اختبر مستواك</Link>
          <Link href="/premium">الاشتراك</Link>
        </nav>
        {wallet && <span className="coin-pill">🪙 {wallet.balance}</span>}
        {user?.is_guest ? (
          <Link href="/login" className="btn ghost" style={{ padding: '7px 14px' }}>
            إنشاء حساب
          </Link>
        ) : (
          <span style={{ fontSize: 14, color: 'var(--ink-soft)' }}>
            {user?.full_name || user?.email}
          </span>
        )}
      </div>
    </header>
  );
}
