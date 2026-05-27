import type { ExtractionTrace } from '../../types';

export function ProcessingTrace({ trace }: { trace?: ExtractionTrace | null }) {
  if (!trace) {
    return null;
  }

  const usedChunks = new Set(trace.context_package.chunk_ids);

  return (
    <section className="tracePanel" aria-label="Processing trace">
      <div className="panelHeader">
        <div>
          <h3>Processing Trace</h3>
          <p>Preflight, chunking, context budget, model invocation, and merge issues are tracked for review.</p>
        </div>
        <span className={trace.asset.processing_mode === 'sync_allowed' ? 'pill active' : 'pill'}>
          {trace.asset.processing_mode.replaceAll('_', ' ')}
        </span>
      </div>

      <div className="traceGrid">
        <TraceItem label="File size" value={formatBytes(trace.asset.size_bytes)} />
        <TraceItem label="Pages" value={String(trace.asset.page_count)} />
        <TraceItem label="Normalizer" value={trace.normalized_document?.normalizer ?? 'not recorded'} />
        <TraceItem label="Blocks" value={String(trace.normalized_document?.block_count ?? 0)} />
        <TraceItem label="Chunks" value={String(trace.chunks.length)} />
        <TraceItem label="Input tokens" value={String(trace.context_package.estimated_input_tokens)} />
        <TraceItem label="Token budget" value={String(trace.context_package.token_budget)} />
        <TraceItem label="Reserved output" value={String(trace.context_package.reserved_output_tokens)} />
      </div>

      {trace.asset.preflight_issues.length > 0 && (
        <div className="issueList">
          {trace.asset.preflight_issues.map((issue, index) => (
            <div key={`${issue.code}-${index}`} className="issueItem">
              <strong>{issue.code}</strong>
              <span>{issue.message}</span>
            </div>
          ))}
        </div>
      )}

      {trace.normalized_document && (
        <section className="normalizationPreview">
          <div>
            <h4>Normalized Markdown</h4>
            <p>
              {trace.normalized_document.normalizer} v{trace.normalized_document.normalizer_version} · {trace.normalized_document.duration_ms} ms
            </p>
          </div>
          {trace.normalized_document.warnings.length > 0 && (
            <div className="issueList">
              {trace.normalized_document.warnings.map((issue, index) => (
                <div key={`${issue.code}-${index}`} className="issueItem">
                  <strong>{issue.code}</strong>
                  <span>{issue.message}</span>
                </div>
              ))}
            </div>
          )}
          <pre>{trace.normalized_document.markdown_preview}</pre>
        </section>
      )}

      <div className="traceColumns">
        <section>
          <h4>Context Package</h4>
          <p>
            Strategy: <strong>{trace.context_package.assembly_strategy}</strong>
          </p>
          <p>Target fields: {trace.context_package.target_fields.join(', ') || 'custom schema'}</p>
          <p>Chunk ids: {trace.context_package.chunk_ids.join(', ') || 'none'}</p>
        </section>

        <section>
          <h4>Model Invocations</h4>
          {trace.invocations.map((item) => (
            <p key={item.id}>
              {item.provider}/{item.model_name} · {item.status} · {item.duration_ms} ms
            </p>
          ))}
          {trace.invocations.length === 0 && <p>No model invocation recorded.</p>}
        </section>
      </div>

      <section>
        <h4>Document Chunks</h4>
        <div className="chunkList">
          {trace.chunks.map((chunk) => (
            <article key={chunk.id} className={usedChunks.has(chunk.id) ? 'chunkItem used' : 'chunkItem'}>
              <strong>
                #{chunk.chunk_index + 1} · {chunk.source_range}
              </strong>
              <span>{chunk.token_count} tokens</span>
              <p>{chunk.preview || 'Empty chunk'}</p>
            </article>
          ))}
        </div>
      </section>
    </section>
  );
}

function TraceItem({ label, value }: { label: string; value: string }) {
  return (
    <div className="traceItem">
      <span>{label}</span>
      <strong>{value}</strong>
    </div>
  );
}

function formatBytes(value: number): string {
  if (value < 1024) {
    return `${value} B`;
  }
  if (value < 1024 * 1024) {
    return `${(value / 1024).toFixed(1)} KB`;
  }
  return `${(value / 1024 / 1024).toFixed(1)} MB`;
}
