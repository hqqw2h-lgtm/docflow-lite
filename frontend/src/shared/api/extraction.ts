import { request } from './client';
import type { ExtractionResult, ExtractionStatus } from '../types';

export const extractionApi = {
  list: (workspaceId: string) =>
    request<ExtractionResult[]>(`/api/workspaces/${workspaceId}/results`),
  extract: (workspaceId: string, file: File, documentContext = '') => {
    const form = new FormData();
    form.append('file', file);
    form.append('document_context', documentContext);
    return request<ExtractionResult>(`/api/workspaces/${workspaceId}/extract`, {
      method: 'POST',
      body: form
    });
  },
  update: (id: string, body: { corrected_data?: unknown; status?: ExtractionStatus }) =>
    request<ExtractionResult>(`/api/results/${id}`, { method: 'PATCH', body: JSON.stringify(body) }),
  analyzeWorkspace: (id: string) =>
    request<{
      prompt_template: string;
      initialization_status: 'active' | 'inactive';
      prompt_profile_id: string;
      prompt_profile_version: number;
      sample_count: number;
    }>(`/api/workspaces/${id}/analyze`, { method: 'POST' })
};
