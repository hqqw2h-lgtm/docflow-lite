import { createContext, useContext, useEffect, useState, type ReactNode } from 'react';
import { api } from '../api';
import type { Tenant } from '../api/types';

interface TenantContextValue {
  tenants: Tenant[];
  tenantId: string;
  setTenantId: (id: string) => void;
  loading: boolean;
}

const Ctx = createContext<TenantContextValue | null>(null);

const STORAGE_KEY = 'docflow.v2.tenantId';

export function TenantProvider({ children }: { children: ReactNode }) {
  const [tenants, setTenants] = useState<Tenant[]>([]);
  const [tenantId, setTenantIdState] = useState('');
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api.listTenants().then((list) => {
      setTenants(list);
      const saved = localStorage.getItem(STORAGE_KEY) ?? '';
      const next = list.find((t) => t.id === saved)?.id ?? list[0]?.id ?? '';
      setTenantIdState(next);
      setLoading(false);
    });
  }, []);

  const setTenantId = (id: string) => {
    setTenantIdState(id);
    localStorage.setItem(STORAGE_KEY, id);
  };

  return <Ctx.Provider value={{ tenants, tenantId, setTenantId, loading }}>{children}</Ctx.Provider>;
}

export function useTenant() {
  const v = useContext(Ctx);
  if (!v) throw new Error('TenantProvider missing');
  return v;
}
