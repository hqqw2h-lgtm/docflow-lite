import { Alert, Descriptions, Drawer, Empty, Spin, Steps, Tag, Typography } from 'antd';
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
                <Steps
                  direction="vertical"
                  size="small"
                  current={trace.spans.length - 1}
                  items={trace.spans.map((s) => ({
                    title: (
                      <>
                        <Typography.Text strong>{s.type}</Typography.Text>{' '}
                        <Tag color={STATUS_COLOR[s.status] ?? 'default'}>{s.status}</Tag>
                        <Typography.Text type="secondary"> {s.duration_ms} ms</Typography.Text>
                      </>
                    ),
                    description: (
                      <div style={{ marginTop: 4 }}>
                        {s.error ? (
                          <Alert type="error" message={s.error} style={{ marginBottom: 8 }} showIcon />
                        ) : null}
                        {Object.keys(s.input_summary || {}).length ? (
                          <div style={{ marginBottom: 6 }}>
                            <Typography.Text type="secondary">input:</Typography.Text>
                            <JsonView value={s.input_summary} maxHeight={160} />
                          </div>
                        ) : null}
                        {Object.keys(s.output_summary || {}).length ? (
                          <div>
                            <Typography.Text type="secondary">output:</Typography.Text>
                            <JsonView value={s.output_summary} maxHeight={160} />
                          </div>
                        ) : null}
                      </div>
                    ),
                  }))}
                />
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
