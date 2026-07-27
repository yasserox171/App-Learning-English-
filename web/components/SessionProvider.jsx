'use client';

import { createContext, useContext, useEffect, useState } from 'react';
import { api, ensureSession } from '../lib/api';

const SessionContext = createContext({ user: null, loading: true });

export function useSession() {
  return useContext(SessionContext);
}

/**
 * Bootstraps a session on first paint (v2 §2.1): reuse the stored JWT, or
 * silently create a guest account. Nothing is ever gated behind signup.
 */
export function SessionProvider({ children }) {
  const [user, setUser] = useState(null);
  const [wallet, setWallet] = useState(null);
  const [loading, setLoading] = useState(true);

  const refreshWallet = async () => {
    try {
      setWallet(await api.wallet());
    } catch {
      /* wallet is decorative in the header */
    }
  };

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const me = await ensureSession();
        if (!cancelled) setUser(me);
        await refreshWallet();
      } catch {
        /* offline — pages render their own empty states */
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  return (
    <SessionContext.Provider
      value={{ user, setUser, wallet, refreshWallet, loading }}
    >
      {children}
    </SessionContext.Provider>
  );
}
