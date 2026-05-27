import { isApiNotFound, request } from './client';
import type { TrainingExample, TrainingExampleSet } from '../types';

export const samplesApi = {
  listExamples: (workspaceId: string) =>
    request<TrainingExample[]>(`/api/workspaces/${workspaceId}/training-examples`),
  listSets: async (workspaceId: string): Promise<TrainingExampleSet[]> => {
    const path = `/api/workspaces/${workspaceId}/example-sets`;
    try {
      return await request<TrainingExampleSet[]>(path);
    } catch (error) {
      if (!isApiNotFound(error, 'GET', path)) throw error;
      const examples = await request<TrainingExample[]>(
        `/api/workspaces/${workspaceId}/training-examples`
      );
      const now = new Date().toISOString();
      return [
        {
          id: 'legacy-draft',
          workspace_id: workspaceId,
          version: 1,
          name: 'Draft sample batch',
          status: 'draft',
          prompt_profile_id: '',
          examples,
          created_at: now,
          updated_at: now
        }
      ];
    }
  },
  freezeSet: (workspaceId: string, exampleSetId: string) =>
    request<{
      prompt_template: string;
      initialization_status: 'active' | 'inactive';
      prompt_profile_id: string;
      prompt_profile_version: number;
      sample_count: number;
    }>(`/api/workspaces/${workspaceId}/example-sets/${exampleSetId}/freeze`, { method: 'POST' }),
  cloneSet: (workspaceId: string, exampleSetId: string) =>
    request<TrainingExampleSet>(
      `/api/workspaces/${workspaceId}/example-sets/${exampleSetId}/clone`,
      { method: 'POST' }
    ),
  removeExample: (workspaceId: string, exampleSetId: string, exampleId: string) =>
    request<TrainingExampleSet>(
      `/api/workspaces/${workspaceId}/example-sets/${exampleSetId}/examples/${exampleId}`,
      { method: 'DELETE' }
    )
};
