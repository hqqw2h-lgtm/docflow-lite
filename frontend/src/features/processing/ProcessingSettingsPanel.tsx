import { useEffect, useState } from 'react';
import { api } from '../../api';
import type { ProcessingPolicy } from '../../types';

const defaultPolicy: ProcessingPolicy = {
  sync_max_bytes: 2_000_000,
  async_max_bytes: 80_000_000,
  sync_max_pages: 25,
  max_pages: 500,
  chunk_token_limit: 900,
  chunk_overlap_tokens: 80,
  max_candidate_chunks: 8,
  context_token_budget: 6000,
  reserved_output_tokens: 1200,
  raw_text_preview_chars: 12000
};

export function ProcessingSettingsPanel({ onNotice }: { onNotice: (message: string) => void }) {
  const [policy, setPolicy] = useState<ProcessingPolicy>(defaultPolicy);

  useEffect(() => {
    void api.processingPolicy().then(setPolicy).catch((error: Error) => onNotice(error.message));
  }, [onNotice]);

  const save = async () => {
    try {
      const saved = await api.saveProcessingPolicy(policy);
      setPolicy(saved);
      onNotice('Processing policy saved.');
    } catch (error) {
      onNotice((error as Error).message);
    }
  };

  const update = (key: keyof ProcessingPolicy, value: string) => {
    setPolicy({ ...policy, [key]: Number(value) });
  };

  return (
    <section className="panel narrow">
      <h2>Processing Settings</h2>
      <p>Control large file preflight, chunking, candidate selection, and model context budget.</p>
      <div className="settingsGrid">
        <NumberInput label="Sync max bytes" value={policy.sync_max_bytes} onChange={(value) => update('sync_max_bytes', value)} />
        <NumberInput label="Async max bytes" value={policy.async_max_bytes} onChange={(value) => update('async_max_bytes', value)} />
        <NumberInput label="Sync max pages" value={policy.sync_max_pages} onChange={(value) => update('sync_max_pages', value)} />
        <NumberInput label="Max pages" value={policy.max_pages} onChange={(value) => update('max_pages', value)} />
        <NumberInput label="Chunk token limit" value={policy.chunk_token_limit} onChange={(value) => update('chunk_token_limit', value)} />
        <NumberInput label="Chunk overlap tokens" value={policy.chunk_overlap_tokens} onChange={(value) => update('chunk_overlap_tokens', value)} />
        <NumberInput label="Max candidate chunks" value={policy.max_candidate_chunks} onChange={(value) => update('max_candidate_chunks', value)} />
        <NumberInput label="Context token budget" value={policy.context_token_budget} onChange={(value) => update('context_token_budget', value)} />
        <NumberInput label="Reserved output tokens" value={policy.reserved_output_tokens} onChange={(value) => update('reserved_output_tokens', value)} />
        <NumberInput label="Markdown preview chars" value={policy.raw_text_preview_chars} onChange={(value) => update('raw_text_preview_chars', value)} />
      </div>
      <button className="primary" onClick={save}>
        Save processing policy
      </button>
    </section>
  );
}

function NumberInput({ label, value, onChange }: { label: string; value: number; onChange: (value: string) => void }) {
  return (
    <label>
      {label}
      <input type="number" min="1" value={value} onChange={(event) => onChange(event.target.value)} />
    </label>
  );
}
