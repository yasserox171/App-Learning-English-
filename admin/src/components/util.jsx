import React, { useEffect, useState } from 'react';

export function useToast() {
  const [toast, setToast] = useState(null);
  useEffect(() => {
    if (!toast) return;
    const t = setTimeout(() => setToast(null), 3500);
    return () => clearTimeout(t);
  }, [toast]);
  const show = (message, error = false) => setToast({ message, error });
  const node = toast ? (
    <div className={`toast${toast.error ? ' error' : ''}`}>{toast.message}</div>
  ) : null;
  return [show, node];
}

export function StatusBadge({ status }) {
  const map = {
    published: 'ok',
    draft: 'warn',
    rejected: 'bad',
    active: 'ok',
    completed: 'info',
  };
  return <span className={`badge ${map[status] || 'muted'}`}>{status}</span>;
}

export function fmtDate(value) {
  if (!value) return '—';
  return new Date(value).toLocaleString();
}
