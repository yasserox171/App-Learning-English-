'use client';

import { useEffect, useState } from 'react';
import { api } from '../../lib/api';
import { useSession } from '../../components/SessionProvider';

const WHATSAPP = process.env.NEXT_PUBLIC_WHATSAPP_NUMBER || '';

/** Detect Morocco → CMI, everyone else → Stripe (v2 §7.3). */
function detectPrimary(user) {
  const country = (user?.country || '').toLowerCase();
  if (country) return country === 'ma' ? 'cmi' : 'stripe';
  const locale = Intl.DateTimeFormat().resolvedOptions().locale || '';
  return locale.toLowerCase().includes('-ma') ? 'cmi' : 'stripe';
}

export default function PremiumPage() {
  const { user, wallet, refreshWallet, loading } = useSession();
  const [plan, setPlan] = useState('monthly');
  const [primary, setPrimary] = useState('stripe');
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');

  useEffect(() => {
    if (!loading) setPrimary(detectPrimary(user));
  }, [user, loading]);

  const payWithStripe = async () => {
    setBusy(true);
    setError('');
    try {
      const session = await api.stripeCheckout(plan);
      window.location.href = session.url;
    } catch (e) {
      setError(e.message || 'تعذّر بدء عملية الدفع.');
      setBusy(false);
    }
  };

  const payWithCMI = async () => {
    setBusy(true);
    setError('');
    try {
      const { gateway_url: url, fields } = await api.cmiInitiate(plan);
      // CMI is a hosted page reached by POSTing a signed form.
      const form = document.createElement('form');
      form.method = 'POST';
      form.action = url;
      Object.entries(fields).forEach(([name, value]) => {
        const input = document.createElement('input');
        input.type = 'hidden';
        input.name = name;
        input.value = value;
        form.appendChild(input);
      });
      document.body.appendChild(form);
      form.submit();
    } catch (e) {
      setError(e.message || 'تعذّر بدء عملية الدفع.');
      setBusy(false);
    }
  };

  const redeem = async (tier) => {
    setBusy(true);
    try {
      await api.redeem(tier);
      await refreshWallet();
    } catch (e) {
      setError(e.message || 'تعذّر الاستبدال.');
    } finally {
      setBusy(false);
    }
  };

  const primaryPay = primary === 'cmi' ? payWithCMI : payWithStripe;
  const primaryLabel = primary === 'cmi' ? 'الدفع ببطاقة (CMI)' : 'اشترك الآن';

  return (
    <>
      <h1 className="page">⭐ الاشتراك المميز</h1>
      <p className="sub">وصول كامل لجميع الدروس والمستويات ومزايا المدرّس الذكي.</p>

      {wallet?.premium_active && (
        <div className="card">
          <span className="badge ok">
            اشتراكك فعّال حتى {new Date(wallet.premium_until).toLocaleDateString()}
          </span>
        </div>
      )}

      <div className="card">
        <div className="plan-toggle">
          <button
            className={plan === 'monthly' ? 'active' : ''}
            onClick={() => setPlan('monthly')}
          >
            <div className="price">$6</div>
            <div className="per">شهرياً</div>
          </button>
          <button
            className={plan === 'annual' ? 'active' : ''}
            onClick={() => setPlan('annual')}
          >
            <div className="price">$60</div>
            <div className="per">سنوياً — شهران مجاناً</div>
          </button>
        </div>

        {/* One prominent default action (§7.3) */}
        <button
          className="btn primary big pay-primary"
          disabled={busy}
          onClick={primaryPay}
        >
          {busy ? '…' : primaryLabel}
        </button>
        {error && <p className="badge bad">{error}</p>}

        {/* Everything else tucked behind a quiet accordion (§7.3) */}
        <details className="pay-more">
          <summary>طرق دفع أخرى</summary>

          {primary !== 'stripe' && (
            <div className="pay-alt">
              <span>بطاقة دولية (Stripe)</span>
              <button className="btn ghost" onClick={payWithStripe} disabled={busy}>
                متابعة
              </button>
            </div>
          )}
          {primary !== 'cmi' && (
            <div className="pay-alt">
              <span>بطاقة مغربية (CMI)</span>
              <button className="btn ghost" onClick={payWithCMI} disabled={busy}>
                متابعة
              </button>
            </div>
          )}
          <div className="pay-alt">
            <span>
              واتساب / تحويل بنكي
              <div className="delay">التفعيل خلال ~24 ساعة</div>
            </span>
            <a
              className="btn ghost"
              href={
                WHATSAPP
                  ? `https://wa.me/${WHATSAPP}?text=${encodeURIComponent(
                      'أرغب في الاشتراك المميز'
                    )}`
                  : '#'
              }
              target="_blank"
              rel="noreferrer"
            >
              تواصل
            </a>
          </div>
        </details>
      </div>

      {/* Coins path — free premium without paying (§2.3) */}
      {wallet && (
        <div className="card">
          <h3 style={{ marginTop: 0 }}>🪙 أو استبدل عملاتك ({wallet.balance})</h3>
          {wallet.redemption_tiers?.map((tier) => (
            <div className="pay-alt" key={tier.key}>
              <span>
                {tier.days} يوم اشتراك مميز
                <div className="delay">{tier.coins} عملة</div>
              </span>
              <button
                className="btn ok"
                disabled={busy || wallet.balance < tier.coins}
                onClick={() => redeem(tier.key)}
              >
                استبدال
              </button>
            </div>
          ))}
        </div>
      )}
    </>
  );
}
