import { Alert, Descriptions, Drawer, Empty, Popover, Spin, Tag, Typography } from 'antd';
import { useEffect, useState } from 'react';
import { api } from '../api';
import type { Invocation, Trace } from '../api/types';
import { JsonView } from './JsonView';

const STATUS_COLOR: Record<string, string> = {
  completed: 'success',
  needs_review: 'warning',
  failed: 'error',
  running: 'processing',
  queued: 'default',
  ok: 'success',
  error: 'error',
};

function prettifySpanType(type: string): string {
  return type.replaceAll('_', ' ');
}

const LANE_LABEL: Record<string, string> = {
  request_in: 'Request In',
  preflight: 'Preflight',
  normalize: 'Normalize',
  context_assembly: 'Context Assembly',
  model_call: 'Model Call',
  validate: 'Validate',
  final_output: 'Final Output',
};

function hasData(value: unknown): boolean {
  if (value == null) {
    return false;
  }
  if (Array.isArray(value)) {
    return value.length > 0;
  }
  if (typeof value === 'object') {
    return Object.keys(value as Record<string, unknown>).length > 0;
  }
  if (typeof value === 'string') {
    return value.trim().length > 0;
  }
  return true;
}

function summarizeOutput(value: unknown): string {
  if (value == null) {
    return 'no output';
  }
  if (typeof value === 'string') {
    const v = value.trim();
    return v.length > 32 ? `${v.slice(0, 32)}...` : v;
  }
  if (Array.isArray(value)) {
    return `array(${value.length})`;
  }
  if (typeof value === 'object') {
    const keys = Object.keys(value as Record<string, unknown>);
    if (keys.length === 0) {
      return 'object(0)';
    }
    const head = keys.slice(0, 2).join(', ');
    return keys.length > 2 ? `${head}, ...` : head;
  }
  return String(value);
}

export function TraceDrawer({
  invocation,
  onClose,
}: {
  invocation: Invocation | null;
  onClose: () => void;
}) {
  const [trace, setTrace] = useState<Trace | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  useEffect(() => {
    if (!invocation) {
      setTrace(null);
      setError('');
      return;
    }
    setLoading(true);
    setError('');
    api
      .getInvocationTrace(invocation.id)
      .then(setTrace)
      .catch((e: Error) => setError(e.message))
      .finally(() => setLoading(false));
  }, [invocation]);

  return (
    <Drawer
      width={720}
      open={!!invocation}
      onClose={onClose}
      title={
        invocation ? (
          <div>
            <Typography.Text strong>{invocation.file_name || '(no file)'}</Typography.Text>{' '}
            <Tag color={STATUS_COLOR[invocation.status] ?? 'default'}>{invocation.status}</Tag>
            <Tag>{invocation.source}</Tag>
          </div>
        ) : (
          'Trace'
        )
      }
      destroyOnClose
    >
      {!invocation ? null : (
        <>
          <Descriptions size="small" column={2} bordered style={{ marginBottom: 16 }}>
            <Descriptions.Item label="Invocation ID">{invocation.id}</Descriptions.Item>
            <Descriptions.Item label="Duration">{invocation.duration_ms} ms</Descriptions.Item>
            <Descriptions.Item label="Version">{invocation.version_id}</Descriptions.Item>
            <Descriptions.Item label="Model">
              {invocation.model_provider || '-'} / {invocation.model_name || '-'}
            </Descriptions.Item>
            <Descriptions.Item label="Size">{invocation.size_bytes} B</Descriptions.Item>
            <Descriptions.Item label="File type">{invocation.file_type ?? '-'}</Descriptions.Item>
            {invocation.error_message ? (
              <Descriptions.Item label="Error" span={2}>
                <Typography.Text type="danger">
                  [{invocation.error_code}] {invocation.error_message}
                </Typography.Text>
              </Descriptions.Item>
            ) : null}
          </Descriptions>

          {loading ? <Spin /> : null}
          {error ? <Alert type="error" message={error} /> : null}

          {trace ? (
            <>
              <Typography.Title level={5}>Pipeline spans</Typography.Title>
              {trace.spans.length === 0 ? (
                <Empty description="No spans" />
              ) : (
                <>
                  <Typography.Text type="secondary">时序图（上方是请求线，下方是返回线；悬停箭头看该阶段 input / output / error / 耗时）</Typography.Text>
                  <div
                    style={{
                      marginTop: 8,
                      marginBottom: 16,
                      border: '1px solid #f0f0f0',
                      borderRadius: 8,
                      padding: 12,
                      overflowX: 'auto',
                    }}
                  >
                    {(() => {
                      const componentLanes = [
                        'request_in',
                        ...Array.from(new Set(trace.spans.map((span) => span.type))),
                        'final_output',
                      ];
                      const laneGap = 130;
                      const laneStart = 90;
                      const diagramWidth = Math.max(660, laneStart + laneGap * (componentLanes.length - 1) + 90);
                      const getLaneX = (lane: string) => {
                        const index = componentLanes.indexOf(lane);
                        return laneStart + laneGap * (index < 0 ? 0 : index);
                      };

                      return (
                        <>
                    <div
                      style={{
                        position: 'relative',
                        width: diagramWidth,
                        minHeight: 36,
                        marginBottom: 12,
                      }}
                    >
                      {componentLanes.map((lane) => (
                        <div
                          key={lane}
                          style={{
                            position: 'absolute',
                            left: getLaneX(lane) - 60,
                            width: 120,
                            textAlign: 'center',
                          }}
                        >
                          <Tag color={lane === 'request_in' || lane === 'final_output' ? 'geekblue' : 'cyan'}>
                            {LANE_LABEL[lane] ?? prettifySpanType(lane)}
                          </Tag>
                        </div>
                      ))}
                    </div>

                    {trace.spans.map((s, idx) => {
                      const fromLane = idx === 0 ? 'request_in' : trace.spans[idx - 1]?.type || 'request_in';
                      const toLane = s.type;
                      const fromX = getLaneX(fromLane);
                      const toX = getLaneX(toLane);
                      const hasInput = hasData(s.input_summary);
                      const hasOutput = hasData(s.output_summary);
                      const outputLabel = summarizeOutput(s.output_summary);
                      const hoverContent = (
                        <div style={{ width: 420 }}>
                          <div style={{ display: 'flex', alignItems: 'center', gap: 6, flexWrap: 'wrap', marginBottom: 8 }}>
                            <Tag>{prettifySpanType(s.type)}</Tag>
                            <Tag color={STATUS_COLOR[s.status] ?? 'default'}>{s.status}</Tag>
                            <Tag>{s.duration_ms} ms</Tag>
                            <Typography.Text type="secondary" style={{ fontSize: 12 }}>
                              {LANE_LABEL[fromLane] ?? prettifySpanType(fromLane)} → {LANE_LABEL[toLane] ?? prettifySpanType(toLane)}
                            </Typography.Text>
                          </div>
                          {s.error ? <Alert type="error" message={s.error} showIcon style={{ marginBottom: 8 }} /> : null}
                          <div style={{ marginBottom: 8 }}>
                            <Typography.Text type="secondary">input</Typography.Text>
                            {hasInput ? <JsonView value={s.input_summary} maxHeight={180} /> : <Typography.Text type="secondary">（无输入）</Typography.Text>}
                          </div>
                          <div>
                            <Typography.Text type="secondary">output</Typography.Text>
                            {hasOutput ? <JsonView value={s.output_summary} maxHeight={180} /> : <Typography.Text type="secondary">（无输出）</Typography.Text>}
                          </div>
                        </div>
                      );
                      return (
                        <div
                          key={`${s.type}-${s.started_at}-${idx}`}
                          style={{
                            position: 'relative',
                            width: diagramWidth,
                            borderTop: idx === 0 ? 'none' : '1px dashed #f0f0f0',
                            paddingTop: 10,
                            marginTop: idx === 0 ? 0 : 8,
                          }}
                        >
                          <Popover content={hoverContent} trigger="hover" placement="right" overlayStyle={{ maxWidth: 520 }}>
                            <svg width={diagramWidth} height={56} style={{ display: 'block', cursor: 'pointer' }}>
                              {componentLanes.map((lane) => (
                                <line
                                  key={lane}
                                  x1={getLaneX(lane)}
                                  y1={0}
                                  x2={getLaneX(lane)}
                                  y2={56}
                                  stroke="#d9d9d9"
                                  strokeDasharray="3 3"
                                />
                              ))}
                              <text x={(fromX + toX) / 2} y={11} textAnchor="middle" fontSize="12" fill="#595959">
                                {(LANE_LABEL[toLane] ?? prettifySpanType(toLane)) + ` (${s.duration_ms}ms)`}
                              </text>
                              <line x1={fromX} y1={20} x2={toX} y2={20} stroke="#1677ff" strokeWidth={2} />
                              <polygon
                                points={toX >= fromX ? `${toX - 8},15 ${toX},20 ${toX - 8},25` : `${toX + 8},15 ${toX},20 ${toX + 8},25`}
                                fill="#1677ff"
                              />
                              <line x1={toX} y1={36} x2={fromX} y2={36} stroke="#52c41a" strokeWidth={2} />
                              <polygon
                                points={fromX <= toX ? `${fromX + 8},31 ${fromX},36 ${fromX + 8},41` : `${fromX - 8},31 ${fromX},36 ${fromX - 8},41`}
                                fill="#52c41a"
                              />
                              <text x={(fromX + toX) / 2} y={52} textAnchor="middle" fontSize="11" fill="#389e0d">
                                output: {outputLabel}
                              </text>
                            </svg>
                          </Popover>
                        </div>
                      );
                    })}
                        </>
                      );
                    })()}
                  </div>
                </>
              )}

              <Typography.Title level={5} style={{ marginTop: 16 }}>Final output</Typography.Title>
              <JsonView value={invocation.final_output} />
              {invocation.validation_issues?.length ? (
                <>
                  <Typography.Title level={5} style={{ marginTop: 16 }}>Validation issues</Typography.Title>
                  <JsonView value={invocation.validation_issues} maxHeight={200} />
                </>
              ) : null}
            </>
          ) : null}
        </>
      )}
    </Drawer>
  );
}
