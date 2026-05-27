import { request } from './client';
import type { Tenant } from '../types';

export const tenantsApi = {
  list: () => request<Tenant[]>('/api/tenants'),
  create: (body: { name: string; description: string }) =>
    request<Tenant>('/api/tenants', { method: 'POST', body: JSON.stringify(body) })
};
