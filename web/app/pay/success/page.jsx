'use client';

import Link from 'next/link';
import { useEffect } from 'react';
import { useSession } from '../../../components/SessionProvider';

export default function PaySuccessPage() {
  const { refreshWallet } = useSession();

  // The provider's webhook activates premium server-side; re-read the wallet
  // so the UI reflects it as soon as it lands.
  useEffect(() => {
    refreshWallet();
    const timer = setTimeout(refreshWallet, 4000);
    return () => clearTimeout(timer);
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  return (
    <div className="card" style={{ textAlign: 'center', marginTop: 60 }}>
      <h1>🎉 شكراً لك!</h1>
      <p className="sub">
        تم استلام الدفع. سيتم تفعيل اشتراكك خلال لحظات بعد تأكيد المزوّد.
      </p>
      <Link href="/learn" className="btn primary">
        ابدأ التعلّم
      </Link>
    </div>
  );
}
