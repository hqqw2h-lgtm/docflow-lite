import type {
  ExtractionResult,
  ExtractionStatus,
  IntegrationConfig,
  IntegrationWorkflow,
  FieldRuleSuggestion,
  ModelSettings,
  PromptProfile,
  ProcessingPolicy,
  SchemaDefinition,
  Tenant,
  TrainingExample,
  TrainingExampleSet,
  Workspace,
  WorkspaceBackgroundFile,
  WorkspaceBackgroundSummary
} from './types';

const API_BASE = import.meta.env.VITE_API_BASE ?? '';

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, {
    headers: init?.body instanceof FormData ? undefined : { 'Content-Type': 'application/json' },
    ...init
  });
  if (!response.ok) {
    const method = init?.method ?? 'GET';
    const message = await response.text();
    throw new Error(formatApiError(method, path, response.status, response.statusText, message));
  }
  return response.json() as Promise<T>;
}

function formatApiError(method: string, path: string, status: number, statusText: string, body: string): string {
  const detail = parseApiErrorDetail(body);
  const reason = detail || statusText || 'Request failed';
  return `${method} ${path} failed (${status}): ${reason}`;
}

function parseApiErrorDetail(body: string): string {
  if (!body) return '';
  try {
    const parsed = JSON.parse(body) as unknown;
    if (isErrorWithDetail(parsed)) {
      return typeof parsed.detail === 'string' ? parsed.detail : JSON.stringify(parsed.detail);
    }
    return typeof parsed === 'string' ? parsed : JSON.stringify(parsed);
  } catch {
    return body;
  }
}

function isErrorWithDetail(value: unknown): value is { detail: unknown } {
  return typeof value === 'object' && value !== null && 'detail' in value;
}

function isApiNotFound(error: unknown, path: string): boolean {
  return error instanceof Error && error.message.startsWith(`GET ${path} failed (404):`);
}

export const api = {
  tenants: () => request<Tenant[]>('/api/tenants'),
  createTenant: (body: { name: string; description: string }) =>
    request<Tenant>('/api/tenants', { method: 'POST', body: JSON.stringify(body) }),
  workspaces: (params = '') => request<Workspace[]>(`/api/workspaces${params}`),
  createWorkspace: (body: { tenant_id: string; name: string; description: string }) =>
    request<Workspace>('/api/workspaces', { method: 'POST', body: JSON.stringify(body) }),
  updateWorkspace: (id: string, body: Partial<Workspace>) =>
    request<Workspace>(`/api/workspaces/${id}`, { method: 'PATCH', body: JSON.stringify(body) }),
  results: (workspaceId: string) => request<ExtractionResult[]>(`/api/workspaces/${workspaceId}/results`),
  trainingExamples: (workspaceId: string) =>
    request<TrainingExample[]>(`/api/workspaces/${workspaceId}/training-examples`),
  promptProfiles: (workspaceId: string) =>
    request<PromptProfile[]>(`/api/workspaces/${workspaceId}/prompt-profiles`),
  exampleSets: async (workspaceId: string) => {
    const path = `/api/workspaces/${workspaceId}/example-sets`;
    try {
      return await request<TrainingExampleSet[]>(path);
    } catch (error) {
      if (!isApiNotFound(error, path)) throw error;
      const examples = await request<TrainingExample[]>(`/api/workspaces/${workspaceId}/training-examples`);
      const now = new Date().toISOString();
      const fallbackSet: TrainingExampleSet = {
        id: 'legacy-draft',
        workspace_id: workspaceId,
        version: 1,
        name: 'Draft sample batch',
        status: 'draft',
        prompt_profile_id: '',
        examples,
        created_at: now,
        updated_at: now
      };
      return [fallbackSet];
    }
  },
  freezeExampleSet: (workspaceId: string, exampleSetId: string) =>
    request<{
      prompt_template: string;
      initialization_status: 'active' | 'inactive';
      prompt_profile_id: string;
      prompt_profile_version: number;
      sample_count: number;
    }>(`/api/workspaces/${workspaceId}/example-sets/${exampleSetId}/freeze`, { method: 'POST' }),
  cloneExampleSet: (workspaceId: string, exampleSetId: string) =>
    request<TrainingExampleSet>(`/api/workspaces/${workspaceId}/example-sets/${exampleSetId}/clone`, { method: 'POST' }),
  removeExampleFromSet: (workspaceId: string, exampleSetId: string, exampleId: string) =>
    request<TrainingExampleSet>(`/api/workspaces/${workspaceId}/example-sets/${exampleSetId}/examples/${exampleId}`, { method: 'DELETE' }),
  activatePromptProfile: (workspaceId: string, profileId: string) =>
    request<Workspace>(`/api/workspaces/${workspaceId}/prompt-profiles/${profileId}/activate`, { method: 'POST' }),
  backgroundFiles: (workspaceId: string) =>
    request<WorkspaceBackgroundFile[]>(`/api/workspaces/${workspaceId}/background-files`),
  uploadBackgroundFile: (workspaceId: string, file: File) => {
    const form = new FormData();
    form.append('file', file);
    return request<WorkspaceBackgroundSummary>(`/api/workspaces/${workspaceId}/background-files`, { method: 'POST', body: form });
  },
  schemaVersions: (workspaceId: string) =>
    request<SchemaDefinition[]>(`/api/workspaces/${workspaceId}/schema-versions`),
  suggestFieldRule: (body: { description: string; field_type: string }) =>
    request<FieldRuleSuggestion>('/api/field-rule-suggestions', { method: 'POST', body: JSON.stringify(body) }),
  extract: (workspaceId: string, file: File, documentContext = '') => {
    const form = new FormData();
    form.append('file', file);
    form.append('document_context', documentContext);
    return request<ExtractionResult>(`/api/workspaces/${workspaceId}/extract`, { method: 'POST', body: form });
  },
  updateResult: (id: string, body: { corrected_data?: unknown; status?: ExtractionStatus }) =>
    request<ExtractionResult>(`/api/results/${id}`, { method: 'PATCH', body: JSON.stringify(body) }),
  analyzeWorkspace: (id: string) =>
    request<{
      prompt_template: string;
      initialization_status: 'active' | 'inactive';
      prompt_profile_id: string;
      prompt_profile_version: number;
      sample_count: number;
    }>(`/api/workspaces/${id}/analyze`, { method: 'POST' }),
  modelSettings: () => request<ModelSettings>('/api/settings/model'),
  saveModelSettings: (body: ModelSettings) =>
    request<ModelSettings>('/api/settings/model', { method: 'PUT', body: JSON.stringify(body) }),
  processingPolicy: () => request<ProcessingPolicy>('/api/settings/processing'),
  saveProcessingPolicy: (body: ProcessingPolicy) =>
    request<ProcessingPolicy>('/api/settings/processing', { method: 'PUT', body: JSON.stringify(body) }),
  modelList: () => request<string[]>('/api/models'),
  integrations: (workspaceId: string) => request<IntegrationWorkflow[]>(`/api/integrations?workspace_id=${workspaceId}`),
  createIntegration: (workspaceId: string, name: string, config: IntegrationConfig) =>
    request<IntegrationWorkflow>('/api/integrations', {
      method: 'POST',
      body: JSON.stringify({ workspace_id: workspaceId, name, config })
    }),
  updateIntegration: (id: string, body: Partial<IntegrationWorkflow>) =>
    request<IntegrationWorkflow>(`/api/integrations/${id}`, { method: 'PATCH', body: JSON.stringify(body) }),
  activateIntegration: (id: string) =>
    request<IntegrationWorkflow>(`/api/integrations/${id}/activate`, { method: 'POST' })
};
