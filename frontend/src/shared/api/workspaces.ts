import { request } from './client';
import type {
  SchemaDefinition,
  Workspace,
  WorkspaceBackgroundFile,
  WorkspaceBackgroundSummary
} from '../types';

export const workspacesApi = {
  list: (params: { tenantId?: string; query?: string; active?: string } = {}) => {
    const search = new URLSearchParams();
    if (params.tenantId) search.set('tenant_id', params.tenantId);
    if (params.query) search.set('query', params.query);
    if (params.active) search.set('active', params.active);
    const suffix = search.size ? `?${search.toString()}` : '';
    return request<Workspace[]>(`/api/workspaces${suffix}`);
  },
  get: (id: string) => request<Workspace>(`/api/workspaces/${id}`),
  create: (body: { tenant_id: string; name: string; description: string }) =>
    request<Workspace>('/api/workspaces', { method: 'POST', body: JSON.stringify(body) }),
  update: (id: string, body: Partial<Workspace>) =>
    request<Workspace>(`/api/workspaces/${id}`, { method: 'PATCH', body: JSON.stringify(body) }),
  schemaVersions: (id: string) => request<SchemaDefinition[]>(`/api/workspaces/${id}/schema-versions`),
  backgroundFiles: (id: string) => request<WorkspaceBackgroundFile[]>(`/api/workspaces/${id}/background-files`),
  uploadBackgroundFile: (id: string, file: File) => {
    const form = new FormData();
    form.append('file', file);
    return request<WorkspaceBackgroundSummary>(`/api/workspaces/${id}/background-files`, {
      method: 'POST',
      body: form
    });
  }
};
