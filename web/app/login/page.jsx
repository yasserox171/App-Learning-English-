'use client';

import { useRouter } from 'next/navigation';
import { useState } from 'react';
import { api } from '../../lib/api';
import { useSession } from '../../components/SessionProvider';

/**
 * Sign in / create an account. Registering while a guest token is held
 * converts that same row in place — coins and progress carry over (§2.1).
 */
export default function LoginPage() {
  const router = useRouter();
  const { user, setUser } = useSession();
  const [mode, setMode] = useState('register');
  const [form, setForm] = useState({ email: '', password: '', full_name: '' });
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);

  const submit = async (e) => {
    e.preventDefault();
    setBusy(true);
    setError('');
    try {
      const next =
        mode === 'login'
          ? await api.login(form.email, form.password)
          : await api.register({ ...form, app_language: 'ar' });
      setUser(next);
      router.push('/');
    } catch (err) {
      setError(err.message || 'حدث خطأ، حاول مرة أخرى.');
    } finally {
      setBusy(false);
    }
  };

  return (
    <>
      <h1 className="page">
        {mode === 'login' ? 'تسجيل الدخول' : 'إنشاء حساب'}
      </h1>
      {user?.is_guest && (
        <p className="sub">
          أنت تتصفّح كضيف — أنشئ حساباً حتى لا تفقد عملاتك وتقدّمك عند تغيير
          الجهاز.
        </p>
      )}

      <form className="card" onSubmit={submit}>
        {mode === 'register' && (
          <input
            className="option"
            placeholder="الاسم الكامل"
            value={form.full_name}
            onChange={(e) => setForm({ ...form, full_name: e.target.value })}
          />
        )}
        <input
          className="option"
          type="email"
          required
          placeholder="البريد الإلكتروني"
          value={form.email}
          onChange={(e) => setForm({ ...form, email: e.target.value })}
        />
        <input
          className="option"
          type="password"
          required
          minLength={8}
          placeholder="كلمة المرور"
          value={form.password}
          onChange={(e) => setForm({ ...form, password: e.target.value })}
        />
        {error && <p className="badge bad">{error}</p>}
        <button className="btn primary big" disabled={busy}>
          {busy ? '…' : mode === 'login' ? 'دخول' : 'إنشاء الحساب'}
        </button>
        <p style={{ textAlign: 'center', marginBottom: 0 }}>
          <button
            type="button"
            className="btn ghost"
            style={{ marginTop: 10 }}
            onClick={() => setMode(mode === 'login' ? 'register' : 'login')}
          >
            {mode === 'login' ? 'ليس لديك حساب؟ أنشئ حساباً' : 'لديك حساب؟ سجّل الدخول'}
          </button>
        </p>
      </form>
    </>
  );
}
