import { ReloadOutlined } from '@ant-design/icons';
import { Button, Card, Empty, Form, Input, message, Select, Space, Spin, Table, Tag, Typography } from 'antd';
import { useEffect, useState } from 'react';
import { api } from '../api';
import type { Invocation } from '../api/types';
import { TraceDrawer } from '../components/TraceDrawer';

const STATUS_COLOR: Record<string, string> = {
  completed: 'green', needs_review: 'orange', failed: 'red', running: 'blue', queued: 'default',
};

const STATUSES = ['', 'completed', 'needs_review', 'failed', 'running', 'queued'];
const SOURCES = ['', 'ui', 'api_sync', 'api_async', 'sample', 'replay'];

export function AdminInvocationsPage({ admin = true }: { admin?: boolean }) {
  const [list, setList] = useState<Invocation[]>([]);
  const [loading, setLoading] = useState(false);
  const [filters, setFilters] = useState({ status: '', source: '', file_name_contains: '', space_id: '' });
  const [open, setOpen] = useState<Invocation | null>(null);

  const reload = () => {
    setLoading(true);
    const fetcher = admin ? api.adminListInvocations(filters) : api.listInvocations(filters);
    fetcher
      .then(setList)
      .catch((e: Error) => message.error(e.message))
      .finally(() => setLoading(false));
  };

  useEffect(reload, []);

  return (
    <Card
      title={
        <Space>
          <Typography.Title level={4} style={{ margin: 0 }}>
            {admin ? 'Admin · Invocations' : 'Invocations'}
          </Typography.Title>
          <Typography.Text type="secondary">
            {admin
              ? 'Full call history across all SchemaSpaces. Click a row to see the entire trace.'
              : 'Recent calls. Click a row to inspect.'}
          </Typography.Text>
        </Space>
      }
      extra={<Button icon={<ReloadOutlined />} onClick={reload}>Refresh</Button>}
    >
      <Form layout="inline" style={{ marginBottom: 16 }}>
        {admin ? (
          <Form.Item label="Space ID">
            <Input value={filters.space_id} onChange={(e) => setFilters({ ...filters, space_id: e.target.value })} allowClear />
          </Form.Item>
        ) : null}
        <Form.Item label="Status">
          <Select
            style={{ width: 160 }}
            value={filters.status}
            options={STATUSES.map((s) => ({ value: s, label: s || '(any)' }))}
            onChange={(v) => setFilters({ ...filters, status: v })}
          />
        </Form.Item>
        <Form.Item label="Source">
          <Select
            style={{ width: 160 }}
            value={filters.source}
            options={SOURCES.map((s) => ({ value: s, label: s || '(any)' }))}
            onChange={(v) => setFilters({ ...filters, source: v })}
          />
        </Form.Item>
        {admin ? (
          <Form.Item label="File contains">
            <Input value={filters.file_name_contains} onChange={(e) => setFilters({ ...filters, file_name_contains: e.target.value })} allowClear />
          </Form.Item>
        ) : null}
        <Form.Item>
          <Button type="primary" onClick={reload}>Apply</Button>
        </Form.Item>
      </Form>

      {loading ? (
        <Spin />
      ) : list.length === 0 ? (
        <Empty description="No invocations" />
      ) : (
        <Table<Invocation>
          rowKey="id"
          dataSource={list}
          pagination={{ pageSize: 20, showSizeChanger: true }}
          onRow={(r) => ({ onClick: () => setOpen(r), style: { cursor: 'pointer' } })}
          columns={[
            { title: 'File', dataIndex: 'file_name', ellipsis: true },
            { title: 'Status', dataIndex: 'status', width: 120, render: (s: string) => <Tag color={STATUS_COLOR[s] ?? 'default'}>{s}</Tag> },
            { title: 'Source', dataIndex: 'source', width: 100 },
            { title: 'Model', width: 200, render: (_, r) => `${r.model_provider}/${r.model_name}` },
            { title: 'Duration', dataIndex: 'duration_ms', width: 100, render: (v: number) => `${v} ms` },
            { title: 'Started', dataIndex: 'started_at', width: 180, render: (v: string) => new Date(v).toLocaleString() },
          ]}
        />
      )}

      <TraceDrawer invocation={open} onClose={() => setOpen(null)} />
    </Card>
  );
}
