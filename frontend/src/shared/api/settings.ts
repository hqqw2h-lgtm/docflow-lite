import { request } from './client';
import type { FieldRuleSuggestion, ModelSettings, ProcessingPolicy } from '../types';

export const settingsApi = {
  getModel: () => request<ModelSettings>('/api/settings/model'),
  saveModel: (body: ModelSettings) =>
    request<ModelSettings>('/api/settings/model', { method: 'PUT', body: JSON.stringify(body) }),
  getProcessing: () => request<ProcessingPolicy>('/api/settings/processing'),
  saveProcessing: (body: ProcessingPolicy) =>
    request<ProcessingPolicy>('/api/settings/processing', {
      method: 'PUT',
      body: JSON.stringify(body)
    }),
  modelList: () => request<string[]>('/api/models'),
  suggestFieldRule: (body: { description: string; field_type: string }) =>
    request<FieldRuleSuggestion>('/api/field-rule-suggestions', {
      method: 'POST',
      body: JSON.stringify(body)
    })
};
