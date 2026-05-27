export type FileType = 'pdf' | 'excel' | 'csv' | 'text' | 'json' | 'image' | 'markdown';
export const ALL_FILE_TYPES: FileType[] = ['pdf', 'excel', 'csv', 'text', 'json', 'image', 'markdown'];

export type VersionStatus = 'draft' | 'published' | 'archived';
export type SchemaSpaceStatus = 'draft' | 'active' | 'archived';
export type InvocationSource = 'ui' | 'api_sync' | 'api_async' | 'sample' | 'replay';
export type InvocationStatus = 'queued' | 'running' | 'completed' | 'needs_review' | 'failed';
export type SampleStatus = 'uploaded' | 'extracted' | 'confirmed' | 'rejected' | 'needs_review';

export interface SchemaSpaceDefaults {
  model_provider: string;
  model_name: string;
  system_prompt: string;
  extraction_instruction: string;
  processing_policy: Record<string, unknown>;
}

export interface SchemaSpace {
  id: string;
  tenant_id: string;
  name: string;
  description: string;
  input_file_types: FileType[];
  normalizer_overrides: Record<string, string>;
  schema_info: unknown;
  defaults: SchemaSpaceDefaults;
  status: SchemaSpaceStatus;
  created_at: string;
  updated_at: string;
}

export interface SchemaSpaceCreate {
  tenant_id: string;
  name: string;
  description?: string;
  input_file_types: FileType[];
  defaults?: Partial<SchemaSpaceDefaults>;
}

export interface SchemaSpaceVersion {
  id: string;
  schema_space_id: string;
  version: number;
  name: string;
  status: VersionStatus;
  schema_info: unknown;
  processing_policy: Record<string, unknown>;
  system_prompt: string;
  extraction_instruction: string;
  model_provider: string;
  model_name: string;
  parent_version_id: string;
  sample_count: number;
  published_at: string | null;
  created_at: string;
  updated_at: string;
}

export interface Sample {
  id: string;
  version_id: string;
  file_name: string;
  mime_type: string;
  file_type: FileType;
  size_bytes: number;
  sha256: string;
  document_context: string;
  status: SampleStatus;
  expected_output: unknown;
  model_output: unknown;
  corrected_output: unknown;
  correction_notes: unknown[];
  invocation_id: string;
  created_at: string;
  updated_at: string;
}

export interface Invocation {
  id: string;
  schema_space_id: string;
  version_id: string;
  source: InvocationSource;
  status: InvocationStatus;
  file_name: string;
  mime_type: string;
  file_type: FileType | null;
  size_bytes: number;
  sha256: string;
  document_context: string;
  model_provider: string;
  model_name: string;
  final_output: unknown;
  validation_issues: unknown[];
  error_code: string;
  error_message: string;
  parent_invocation_id: string;
  duration_ms: number;
  started_at: string;
  ended_at: string | null;
}

export interface TraceSpan {
  type: string;
  started_at: string;
  ended_at: string;
  duration_ms: number;
  status: string;
  input_summary: Record<string, unknown>;
  output_summary: Record<string, unknown>;
  error: string;
}

export interface Trace {
  id: string;
  invocation_id: string;
  spans: TraceSpan[];
  model_provider: string;
  model_name: string;
  schema_space_id: string;
  version_id: string;
  created_at: string;
}

export interface Tenant {
  id: string;
  name: string;
  description: string;
  status: string;
  created_at: string;
  updated_at: string;
}

export interface OptimizationReport {
  version_id: string;
  best_combination: Record<string, string>;
  best_score: number;
  applied: boolean;
  trials: {
    overrides: Record<string, string>;
    avg_score: number;
    error_count: number;
    sample_count: number;
    outcomes: {
      sample_id: string;
      file_name: string;
      score: number;
      error: string;
    }[];
  }[];
}
