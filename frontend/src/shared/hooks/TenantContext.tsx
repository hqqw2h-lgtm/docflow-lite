import { createContext, useCallback, useContext, useEffect, useMemo, useState } from 'react';
import type { ReactNode } from 'react';
import { App as AntdApp } from 'antd';
import { tenantsApi } from '../api';
import type { Tenant } from '../types';

interface TenantContextValue {
  tenants: Tenant[];
  tenantId: string;
  selectedTenant: Tenant | null;
  setTenantId: (id: string) => void;
  refresh: () => Promise<void>;
}

const TenantContext = createContext<TenantContextValue | null>(null);

const STORAGE_KEY = 'docflow.tenantId';

export function TenantProvider({ children }: { children: ReactNode }) {
  const [tenants, setTenants] = useState<Tenant[]>([]);
  const [tenantId, setTenantIdState] = useState<string>(() => localStorage.getItem(STORAGE_KEY) ?? '');
  const { message } = AntdApp.useApp();

  const setTenantId = useCallback((id: string) => {
    setTenantIdState(id);
    if (id) {
      localStorage.setItem(STORAGE_KEY, id);
    } else {
      localStorage.removeItem(STORAGE_KEY);
    }
  }, []);

  const refresh = useCallback(async () => {
    try {
      const list = await tenantsApi.list();
      setTenants(list);
      if (!list.find((tenant) => tenant.id === tenantId)) {
        const next = list[0]?.id ?? '';
        setTenantIdState(next);
        if (next) localStorage.setItem(STORAGE_KEY, next);
        else localStorage.removeItem(STORAGE_KEY);
      }
    } catch (error) {
      message.error((error as Error).message);
    }
  }, [tenantId, message]);

  useEffect(() => {
    void refresh();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const value = useMemo<TenantContextValue>(() => {
    const selectedTenant = tenants.find((tenant) => tenant.id === tenantId) ?? null;
    return { tenants, tenantId, selectedTenant, setTenantId, refresh };
  }, [tenants, tenantId, setTenantId, refresh]);

  return <TenantContext.Provider value={value}>{children}</TenantContext.Provider>;
}

export function useTenants(): TenantContextValue {
  const ctx = useContext(TenantContext);
  if (!ctx) {
    throw new Error('useTenants must be used within TenantProvider');
  }
  return ctx;
}
