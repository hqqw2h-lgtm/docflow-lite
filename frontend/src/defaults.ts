import type { ExpectedOutputSchema, IntegrationConfig, OutputFieldType, SchemaField, SchemaGroup, SchemaInfo } from './types';

export const emptyIntegrationConfig = (): IntegrationConfig => ({
  file_entrance: {
    source_type: 'manual_upload',
    account: '',
    folder: '',
    mailbox: '',
    subject_contains: '',
    sender_contains: '',
    attachment_formats: ['pdf', 'msg', 'docx', 'xlsx'],
    time_range_start: '',
    time_range_end: '',
    attachment_required: true
  },
  scheduler: {
    mode: 'manual',
    timezone: Intl.DateTimeFormat().resolvedOptions().timeZone || 'UTC',
    start_date: '',
    end_date: '',
    run_at: '',
    repeat_frequency: 'daily',
    execution_mode: 'specific_times',
    specific_times: [],
    window_start: '',
    window_end: '',
    interval_minutes: 60
  },
  mapping: {
    source_schema: {},
    target_schema: {},
    field_mappings: [],
    transformations: {},
    output_preview: {}
  },
  destination: {
    name: '',
    description: '',
    method: 'POST',
    url: '',
    authentication: 'oauth2',
    headers: {},
    connection_timeout_seconds: 180,
    read_timeout_seconds: 180,
    client_id: '',
    client_secret: '',
    token_service_url: ''
  },
  variables: [
    { name: 'workspace_id', type: 'string', value: 'System global variable', entries: {} },
    { name: 'document_id', type: 'string', value: 'System global variable', entries: {} },
    { name: 'extraction_id', type: 'string', value: 'System global variable', entries: {} }
  ]
});

export const newOutputField = (type: OutputFieldType = 'string'): SchemaField => ({
  fieldName: '',
  type,
  isRequired: false,
  regexPattern: '',
  ignored: false,
  constraints: {},
  children: type === 'json' || type === 'jsonArray' ? [] : undefined
});

export const defaultExpectedOutputSchema = (): ExpectedOutputSchema => ({
  outputType: 'json',
  children: []
});

export const normalizeExpectedOutputSchema = (schemaInfo: SchemaInfo): ExpectedOutputSchema => {
  if (!Array.isArray(schemaInfo)) {
    const normalized: ExpectedOutputSchema = {
      outputType: schemaInfo.outputType === 'jsonArray' ? 'jsonArray' : 'json',
      children: normalizeFields(schemaInfo.children ?? [])
    };
    return normalized;
  }

  const children = schemaInfo.flatMap((group: SchemaGroup): SchemaField[] => {
    const fields = normalizeFields(group.children ?? []);
    if (group.flag === 'table') {
      return [
        {
          fieldName: toFieldName(group.title || 'items'),
          type: 'jsonArray',
          isRequired: false,
          regexPattern: '',
          ignored: false,
          constraints: {},
          children: fields
        }
      ];
    }
    return fields;
  });

  return { outputType: 'json' as const, children };
};

const normalizeFields = (fields: SchemaField[]): SchemaField[] =>
  fields.map((field) => {
    const type = normalizeType(field.type);
    return {
      fieldName: toFieldName(field.fieldName || 'field'),
      type,
      isRequired: field.isRequired ?? false,
      regexPattern: field.regexPattern ?? '',
      ignored: field.ignored ?? false,
      constraints: field.constraints ?? {},
      children: type === 'json' || type === 'jsonArray' ? normalizeFields(field.children ?? []) : undefined
    };
  });

const normalizeType = (type: string): OutputFieldType => {
  if (['string', 'number', 'boolean', 'date', 'json', 'jsonArray'].includes(type)) {
    return type as OutputFieldType;
  }
  return 'string';
};

const toFieldName = (value: string): string => {
  const compact = value
    .trim()
    .replace(/[^a-zA-Z0-9]+(.)/g, (_, char: string) => char.toUpperCase())
    .replace(/^[A-Z]/, (char) => char.toLowerCase());
  return compact || 'field';
};
