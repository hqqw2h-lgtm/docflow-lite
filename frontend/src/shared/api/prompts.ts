import { request } from './client';
import type { PromptProfile, Workspace } from '../types';

export const promptsApi = {
  list: (workspaceId: string) =>
    request<PromptProfile[]>(`/api/workspaces/${workspaceId}/prompt-profiles`),
  activate: (workspaceId: string, profileId: string) =>
    request<Workspace>(`/api/workspaces/${workspaceId}/prompt-profiles/${profileId}/activate`, {
      method: 'POST'
    })
};
