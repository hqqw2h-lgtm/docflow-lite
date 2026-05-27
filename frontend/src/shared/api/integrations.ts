import { request } from './client';
import type { IntegrationConfig, IntegrationWorkflow } from '../types';

export const integrationsApi = {
  list: (workspaceId: string) =>
    request<IntegrationWorkflow[]>(`/api/integrations?workspace_id=${workspaceId}`),
  create: (workspaceId: string, name: string, config: IntegrationConfig) =>
    request<IntegrationWorkflow>('/api/integrations', {
      method: 'POST',
      body: JSON.stringify({ workspace_id: workspaceId, name, config })
    }),
  update: (id: string, body: Partial<IntegrationWorkflow>) =>
    request<IntegrationWorkflow>(`/api/integrations/${id}`, {
      method: 'PATCH',
      body: JSON.stringify(body)
    }),
  activate: (id: string) =>
    request<IntegrationWorkflow>(`/api/integrations/${id}/activate`, { method: 'POST' })
};
