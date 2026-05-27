export type SchemaTypeName = 'PURCHASE_ORDER' | 'DELIVERY_NOTE' | 'INVOICE' | 'CUSTOM';
export type IntegrationStatus = 'draft' | 'active';
export type WorkspaceStatus = 'active' | 'inactive';
export type ExtractionStatus =
  | 'uploaded'
  | 'preflighted'
  | 'parsed'
  | 'chunked'
  | 'indexed'
  | 'extracting'
  | 'merging'
  | 'to_review'
  | 'completed'
  | 'analyzed'
  | 'correction_required'
  | 'processing_error'
  | 'failed';
export type TrainingExampleStatus =
  | 'uploaded'
  | 'extracted'
  | 'correction_required'
  | 'accepted'
  | 'rejected'
  | 'analyzed'
  | 'processing_error';
export type PromptProfileStatus = 'draft' | 'active' | 'retired';
export type TrainingExampleSetStatus = 'draft' | 'frozen';

export interface SchemaTypeInfo {
  id: string;
  name: SchemaTypeName;
  title: string;
  description: string;
}

export interface Tenant {
  id: string;
  name: string;
  description: string;
  status: 'active' | 'archived';
  created_at: string;
  updated_at: string;
}

export type OutputRootType = 'json' | 'jsonArray';
export type OutputFieldType = 'string' | 'number' | 'boolean' | 'date' | 'json' | 'jsonArray';

export interface SchemaField {
  fieldName: string;
  type: OutputFieldType;
  isRequired: boolean;
  regexPattern?: string;
  ignored?: boolean;
  constraints?: Record<string, unknown>;
  children?: SchemaField[];
}

export interface SchemaGroup {
  title: string;
  flag: 'fieldGroup' | 'table';
  children: SchemaField[];
}

export interface ExpectedOutputSchema {
  outputType: OutputRootType;
  children: SchemaField[];
}

export type SchemaInfo = ExpectedOutputSchema | SchemaGroup[];

export interface FieldRuleSuggestion {
  regexPattern: string;
  constraints: Record<string, unknown>;
  explanation: string;
}

export interface Workspace {
  id: string;
  tenant_id: string;
  name: string;
  description: string;
  schema_type: SchemaTypeName;
  active_status: boolean;
  initialization_status: WorkspaceStatus;
  extracted: boolean;
  active_schema_version_id: string;
  active_prompt_profile_id: string;
  created_at: string;
  updated_at: string;
  schema_info: SchemaInfo;
  prompt_template: string;
}

export interface SchemaDefinition {
  id: string;
  workspace_id: string;
  version: number;
  status: 'active' | 'retired';
  schema_info: SchemaInfo;
  created_at: string;
}

export interface ExtractionResult {
  id: string;
  workspace_id: string;
  normalized_document_id: string;
  file_name: string;
  model: string;
  raw_text: string;
  extracted_data: unknown;
  corrected_data: unknown;
  status: ExtractionStatus;
  created_at: string;
  trace?: ExtractionTrace | null;
}

export interface ModelSettings {
  provider: 'ollama' | 'mock';
  base_url: string;
  model: string;
}

export interface ProcessingPolicy {
  sync_max_bytes: number;
  async_max_bytes: number;
  sync_max_pages: number;
  max_pages: number;
  chunk_token_limit: number;
  chunk_overlap_tokens: number;
  max_candidate_chunks: number;
  context_token_budget: number;
  reserved_output_tokens: number;
  raw_text_preview_chars: number;
}

export interface DocumentAssetTrace {
  id: string;
  file_name: string;
  mime_type: string;
  size_bytes: number;
  sha256: string;
  page_count: number;
  sheet_count: number;
  processing_mode: 'sync_allowed' | 'async_required' | 'rejected_by_policy';
  preflight_status: 'accepted' | 'async_required' | 'rejected';
  preflight_issues: Array<Record<string, string>>;
}

export interface DocumentChunkTrace {
  id: string;
  chunk_index: number;
  chunk_type: string;
  source_range: string;
  token_count: number;
  preview: string;
}

export interface ContextPackageTrace {
  id: string;
  chunk_ids: string[];
  token_budget: number;
  estimated_input_tokens: number;
  reserved_output_tokens: number;
  assembly_strategy: string;
  target_fields: string[];
}

export interface ModelInvocationTrace {
  id: string;
  context_package_id: string;
  provider: string;
  model_name: string;
  estimated_input_tokens: number;
  estimated_output_tokens: number;
  duration_ms: number;
  status: 'completed' | 'failed';
  error_message: string;
}

export interface NormalizedDocumentTrace {
  id: string;
  normalizer: string;
  normalizer_version: string;
  markdown_preview: string;
  block_count: number;
  table_count: number;
  asset_count: number;
  warnings: Array<Record<string, string>>;
  duration_ms: number;
}

export interface ExtractionTrace {
  asset: DocumentAssetTrace;
  normalized_document?: NormalizedDocumentTrace | null;
  chunks: DocumentChunkTrace[];
  context_package: ContextPackageTrace;
  invocations: ModelInvocationTrace[];
  merge_issues: Array<Record<string, string>>;
}

export interface TrainingExample {
  id: string;
  workspace_id: string;
  extraction_result_id: string;
  expected_output: unknown;
  model_output: unknown;
  corrected_output: unknown;
  status: TrainingExampleStatus;
  correction_notes: Array<Record<string, string>>;
  prompt_profile_id: string;
  created_at: string;
  updated_at: string;
}

export interface TrainingExampleSet {
  id: string;
  workspace_id: string;
  version: number;
  name: string;
  status: TrainingExampleSetStatus;
  prompt_profile_id: string;
  examples: TrainingExample[];
  created_at: string;
  updated_at: string;
}

export interface PromptProfile {
  id: string;
  workspace_id: string;
  version: number;
  status: PromptProfileStatus;
  system_prompt: string;
  extraction_instruction: string;
  output_contract: SchemaInfo;
  few_shot_examples: Array<Record<string, unknown>>;
  field_rules: Array<Record<string, unknown>>;
  validation_rules: Array<Record<string, unknown>>;
  model_provider: string;
  model_name: string;
  created_at: string;
}

export interface WorkspaceBackgroundFile {
  id: string;
  workspace_id: string;
  file_name: string;
  mime_type: string;
  size_bytes: number;
  extracted_text: string;
  ai_summary: string;
  created_at: string;
}

export interface WorkspaceBackgroundSummary {
  file: WorkspaceBackgroundFile;
  workspace: Workspace;
  suggested_description: string;
}

export interface WorkflowVariable {
  name: string;
  type: 'string' | 'dict';
  value: string;
  entries: Record<string, string>;
}

export interface IntegrationConfig {
  file_entrance: {
    source_type: 'manual_upload' | 'outlook' | 'api' | 'shared_folder';
    account: string;
    folder: string;
    mailbox: string;
    subject_contains: string;
    sender_contains: string;
    attachment_formats: string[];
    time_range_start: string;
    time_range_end: string;
    attachment_required: boolean;
  };
  scheduler: {
    mode: 'manual' | 'once' | 'recurring';
    timezone: string;
    start_date: string;
    end_date: string;
    run_at: string;
    repeat_frequency: 'daily' | 'weekly' | 'monthly';
    execution_mode: 'specific_times' | 'time_window';
    specific_times: string[];
    window_start: string;
    window_end: string;
    interval_minutes: number;
  };
  mapping: {
    source_schema: unknown;
    target_schema: unknown;
    field_mappings: Array<{ source: string; target: string }>;
    transformations: Record<string, string>;
    output_preview: unknown;
  };
  destination: {
    name: string;
    description: string;
    method: 'POST' | 'PUT' | 'PATCH';
    url: string;
    authentication: 'none' | 'basic' | 'bearer' | 'oauth2';
    headers: Record<string, string>;
    connection_timeout_seconds: number;
    read_timeout_seconds: number;
    client_id: string;
    client_secret: string;
    token_service_url: string;
  };
  variables: WorkflowVariable[];
}

export interface IntegrationWorkflow {
  id: string;
  workspace_id: string;
  name: string;
  status: IntegrationStatus;
  config: IntegrationConfig;
  created_at: string;
  updated_at: string;
}
