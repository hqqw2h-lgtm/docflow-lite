import { http } from './client';
import type {
  Invocation,
  OptimizationReport,
  Sample,
  SchemaSpace,
  SchemaSpaceCreate,
  SchemaSpaceVersion,
  Tenant,
  Trace,
} from './types';

export const api = {
  listTenants: () => http.get<Tenant[]>('/api/tenants'),

  listSpaces: (tenantId: string) =>
    http.get<SchemaSpace[]>(`/api/schema-spaces?tenant_id=${encodeURIComponent(tenantId)}`),
  getSpace: (id: string) => http.get<SchemaSpace>(`/api/schema-spaces/${id}`),
  createSpace: (payload: SchemaSpaceCreate) => http.post<SchemaSpace>('/api/schema-spaces', payload),
  updateSpace: (id: string, payload: Partial<SchemaSpaceCreate>) =>
    http.patch<SchemaSpace>(`/api/schema-spaces/${id}`, payload),
  effectiveConfig: (id: string, versionId?: string) =>
    http.get<Record<string, unknown>>(
      `/api/schema-spaces/${id}/effective-config${versionId ? `?version_id=${versionId}` : ''}`,
    ),

  listVersions: (spaceId: string) =>
    http.get<SchemaSpaceVersion[]>(`/api/schema-spaces/${spaceId}/versions`),
  getVersion: (spaceId: string, versionId: string) =>
    http.get<SchemaSpaceVersion>(`/api/schema-spaces/${spaceId}/versions/${versionId}`),
  createVersion: (spaceId: string, payload: { name?: string; schema_info?: unknown; parent_version_id?: string }) =>
    http.post<SchemaSpaceVersion>(`/api/schema-spaces/${spaceId}/versions`, {
      schema_space_id: spaceId,
      ...payload,
    }),
  updateVersion: (spaceId: string, versionId: string, payload: Record<string, unknown>) =>
    http.patch<SchemaSpaceVersion>(`/api/schema-spaces/${spaceId}/versions/${versionId}`, payload),
  publishVersion: (spaceId: string, versionId: string) =>
    http.post<SchemaSpaceVersion>(`/api/schema-spaces/${spaceId}/versions/${versionId}/publish`),
  cloneVersion: (spaceId: string, versionId: string) =>
    http.post<SchemaSpaceVersion>(`/api/schema-spaces/${spaceId}/versions/${versionId}/clone`),
  archiveVersion: (spaceId: string, versionId: string) =>
    http.post<SchemaSpaceVersion>(`/api/schema-spaces/${spaceId}/versions/${versionId}/archive`),

  listSamples: (spaceId: string, versionId: string) =>
    http.get<Sample[]>(`/api/schema-spaces/${spaceId}/versions/${versionId}/samples`),
  uploadSample: (
    spaceId: string,
    versionId: string,
    file: File,
    expected: string,
    documentContext: string,
  ) => {
    const fd = new FormData();
    fd.append('file', file);
    fd.append('expected_output', expected);
    fd.append('document_context', documentContext);
    return http.upload<Sample>(`/api/schema-spaces/${spaceId}/versions/${versionId}/samples`, fd);
  },
  confirmSample: (spaceId: string, versionId: string, sampleId: string, corrected?: unknown) =>
    http.post<Sample>(
      `/api/schema-spaces/${spaceId}/versions/${versionId}/samples/${sampleId}/confirm`,
      corrected !== undefined ? { corrected_output: corrected } : undefined,
    ),
  rejectSample: (spaceId: string, versionId: string, sampleId: string) =>
    http.post<Sample>(`/api/schema-spaces/${spaceId}/versions/${versionId}/samples/${sampleId}/reject`),

  runOptimizer: (spaceId: string, versionId: string, apply: boolean) =>
    http.post<OptimizationReport>(
      `/api/schema-spaces/${spaceId}/versions/${versionId}/optimize?apply=${apply}`,
    ),
  lastOptimization: (spaceId: string, versionId: string) =>
    http.get<{ version_id: string; report: OptimizationReport | null }>(
      `/api/schema-spaces/${spaceId}/versions/${versionId}/optimize/last`,
    ),

  invoke: (spaceId: string, versionId: string, file: File, documentContext: string) => {
    const fd = new FormData();
    fd.append('file', file);
    fd.append('document_context', documentContext);
    fd.append('source', 'ui');
    return http.upload<Invocation>(`/api/schema-spaces/${spaceId}/versions/${versionId}/invoke`, fd);
  },

  listInvocations: (params: { space_id?: string; version_id?: string; limit?: number } = {}) => {
    const search = new URLSearchParams();
    if (params.space_id) search.set('space_id', params.space_id);
    if (params.version_id) search.set('version_id', params.version_id);
    search.set('limit', String(params.limit ?? 50));
    return http.get<Invocation[]>(`/api/invocations?${search.toString()}`);
  },
  getInvocation: (id: string) => http.get<Invocation>(`/api/invocations/${id}`),
  getInvocationTrace: (id: string) => http.get<Trace>(`/api/invocations/${id}/trace`),

  replayInvocation: (invocationId: string) =>
    http.post<Invocation>(`/api/admin/invocations/${invocationId}/replay`),

  adminListInvocations: (params: {
    space_id?: string;
    version_id?: string;
    source?: string;
    status?: string;
    file_name_contains?: string;
    limit?: number;
  } = {}) => {
    const search = new URLSearchParams();
    for (const [k, v] of Object.entries(params)) {
      if (v !== undefined && v !== '' && v !== null) search.set(k, String(v));
    }
    if (!search.has('limit')) search.set('limit', '200');
    return http.get<Invocation[]>(`/api/admin/invocations?${search.toString()}`);
  },
};

export type * from './types';
