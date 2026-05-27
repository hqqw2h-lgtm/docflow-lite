import { PlusOutlined, ReloadOutlined, SettingOutlined } from '@ant-design/icons';
import {
  Alert, Button, Card, Descriptions, Empty, Form, Input, message, Modal, Space, Spin, Table, Tabs, Tag, Typography,
} from 'antd';
import { useEffect, useState } from 'react';
import { Link, useNavigate, useParams } from 'react-router-dom';
import { api } from '../api';
import type { FileType, SchemaSpace, SchemaSpaceVersion } from '../api/types';
import { JsonView } from '../components/JsonView';

const STATUS_COLOR: Record<string, string> = {
  draft: 'gold', published: 'green', archived: 'default',
};

export function SchemaSpaceDetailPage() {
  const { spaceId = '' } = useParams();
  const nav = useNavigate();
  const [space, setSpace] = useState<SchemaSpace | null>(null);
  const [versions, setVersions] = useState<SchemaSpaceVersion[]>([]);
  const [loading, setLoading] = useState(true);
  const [defaultsOpen, setDefaultsOpen] = useState(false);
  const [effective, setEffective] = useState<Record<string, unknown> | null>(null);
  const [newVerOpen, setNewVerOpen] = useState(false);
  const [newVerForm] = Form.useForm();
  const [defaultsForm] = Form.useForm();
  const [schemaEditOpen, setSchemaEditOpen] = useState(false);
  const [schemaText, setSchemaText] = useState('');

  const reload = () => {
    setLoading(true);
    Promise.all([api.getSpace(spaceId), api.listVersions(spaceId)])
      .then(([s, v]) => {
        setSpace(s);
        setVersions(v);
      })
      .catch((e: Error) => message.error(e.message))
      .finally(() => setLoading(false));
  };

  useEffect(() => { if (spaceId) reload(); }, [spaceId]);
  useEffect(() => {
    if (spaceId) api.effectiveConfig(spaceId).then(setEffective).catch(() => {/**/});
  }, [spaceId]);

  if (loading || !space) return <Spin />;

  const onCreateVersion = async () => {
    const values = await newVerForm.validateFields();
    try {
      const v = await api.createVersion(spaceId, {
        name: values.name,
        parent_version_id: values.parent_version_id || '',
      });
      message.success(`Created v${v.version}`);
      setNewVerOpen(false);
      newVerForm.resetFields();
      nav(`/spaces/${spaceId}/versions/${v.id}`);
    } catch (e) {
      message.error((e as Error).message);
    }
  };

  const onSaveDefaults = async () => {
    const values = await defaultsForm.validateFields();
    try {
      await api.updateSpace(spaceId, {
        name: values.name,
        description: values.description,
        defaults: {
          model_provider: values.model_provider ?? '',
          model_name: values.model_name ?? '',
          system_prompt: values.system_prompt ?? '',
          extraction_instruction: values.extraction_instruction ?? '',
        },
      });
      message.success('Saved');
      setDefaultsOpen(false);
      reload();
    } catch (e) {
      message.error((e as Error).message);
    }
  };

  return (
    <Space direction="vertical" size={16} style={{ width: '100%' }}>
      <Card
        title={
          <Space>
            <Link to="/spaces"><Typography.Text type="secondary">SchemaSpaces</Typography.Text></Link>
            <Typography.Text type="secondary">/</Typography.Text>
            <Typography.Title level={4} style={{ margin: 0 }}>{space.name}</Typography.Title>
            <Tag color={STATUS_COLOR[space.status] ?? 'default'}>{space.status}</Tag>
          </Space>
        }
        extra={
          <Space>
            <Button icon={<ReloadOutlined />} onClick={reload}>Refresh</Button>
            <Button
              icon={<SettingOutlined />}
              onClick={() => {
                defaultsForm.setFieldsValue({
                  name: space.name,
                  description: space.description,
                  model_provider: space.defaults.model_provider,
                  model_name: space.defaults.model_name,
                  system_prompt: space.defaults.system_prompt,
                  extraction_instruction: space.defaults.extraction_instruction,
                });
                setDefaultsOpen(true);
              }}
            >Edit defaults</Button>
          </Space>
        }
      >
        <Descriptions size="small" column={2}>
          <Descriptions.Item label="ID">{space.id}</Descriptions.Item>
          <Descriptions.Item label="Tenant">{space.tenant_id}</Descriptions.Item>
          <Descriptions.Item label="Description" span={2}>
            {space.description || <Typography.Text type="secondary">No description</Typography.Text>}
          </Descriptions.Item>
          <Descriptions.Item label="Accepted file types" span={2}>
            {space.input_file_types.map((t: FileType) => <Tag key={t}>{t}</Tag>)}
          </Descriptions.Item>
          <Descriptions.Item label="Default model">
            {space.defaults.model_provider || '-'} / {space.defaults.model_name || '-'}
          </Descriptions.Item>
          <Descriptions.Item label="Normalizer overrides">
            {Object.keys(space.normalizer_overrides).length === 0
              ? <Typography.Text type="secondary">auto (set by Optimizer)</Typography.Text>
              : Object.entries(space.normalizer_overrides).map(([k, v]) => <Tag key={k}>{k}: {v}</Tag>)}
          </Descriptions.Item>
        </Descriptions>
      </Card>

      <Card
        title={<Typography.Title level={5} style={{ margin: 0 }}>Versions</Typography.Title>}
        extra={<Button type="primary" icon={<PlusOutlined />} onClick={() => setNewVerOpen(true)}>New draft</Button>}
      >
        <Alert
          type="info"
          showIcon
          style={{ marginBottom: 12 }}
          message="A SchemaSpace can host multiple published versions concurrently. Published versions are immutable — clone to iterate."
        />
        {versions.length === 0 ? (
          <Empty description="No versions yet" />
        ) : (
          <Table<SchemaSpaceVersion>
            rowKey="id"
            dataSource={versions}
            pagination={false}
            columns={[
              {
                title: 'v',
                dataIndex: 'version',
                width: 60,
                render: (v: number, r) => (
                  <Link to={`/spaces/${spaceId}/versions/${r.id}`}>v{v}</Link>
                ),
              },
              { title: 'Name', dataIndex: 'name' },
              {
                title: 'Status',
                dataIndex: 'status',
                width: 110,
                render: (s) => <Tag color={STATUS_COLOR[s] ?? 'default'}>{s}</Tag>,
              },
              { title: 'Samples', dataIndex: 'sample_count', width: 80 },
              {
                title: 'Model',
                render: (_, r) => r.model_provider
                  ? `${r.model_provider}/${r.model_name}`
                  : <Typography.Text type="secondary">inherits</Typography.Text>,
              },
              {
                title: 'Published',
                dataIndex: 'published_at',
                render: (v) => v ? new Date(v).toLocaleString() : '-',
              },
            ]}
          />
        )}
      </Card>

      <Card
        title={<Typography.Title level={5} style={{ margin: 0 }}>Effective configuration</Typography.Title>}
        size="small"
      >
        <Typography.Paragraph type="secondary" style={{ marginBottom: 8 }}>
          What the pipeline actually runs with for this space (source: <code>version</code> / <code>space</code> / <code>system</code>).
        </Typography.Paragraph>
        {effective ? <JsonView value={effective} maxHeight={280} /> : <Spin />}
      </Card>

      <Modal title="New draft version" open={newVerOpen} onOk={onCreateVersion} onCancel={() => setNewVerOpen(false)}>
        <Form form={newVerForm} layout="vertical">
          <Form.Item name="name" label="Name" rules={[{ max: 80 }]}>
            <Input placeholder="e.g. 2026-Q2 redesign" />
          </Form.Item>
          <Form.Item name="parent_version_id" label="Clone from (optional)">
            <Input placeholder="Leave blank to start from default schema" />
          </Form.Item>
        </Form>
      </Modal>

      <Modal
        title="Edit SchemaSpace defaults"
        open={defaultsOpen}
        onOk={onSaveDefaults}
        onCancel={() => setDefaultsOpen(false)}
        width={620}
      >
        <Form form={defaultsForm} layout="vertical">
          <Form.Item name="name" label="Name" rules={[{ required: true, max: 80 }]}>
            <Input />
          </Form.Item>
          <Form.Item name="description" label="Description">
            <Input.TextArea rows={2} />
          </Form.Item>
          <Tabs
            items={[
              {
                key: 'model',
                label: 'Model',
                children: (
                  <>
                    <Form.Item name="model_provider" label="Provider" tooltip="empty = system default">
                      <Input placeholder="ollama / mock" />
                    </Form.Item>
                    <Form.Item name="model_name" label="Model name">
                      <Input placeholder="llama3.1 / mock" />
                    </Form.Item>
                  </>
                ),
              },
              {
                key: 'prompt',
                label: 'Prompts',
                children: (
                  <>
                    <Form.Item name="system_prompt" label="System prompt">
                      <Input.TextArea rows={4} />
                    </Form.Item>
                    <Form.Item name="extraction_instruction" label="Extraction instruction">
                      <Input.TextArea rows={4} />
                    </Form.Item>
                  </>
                ),
              },
            ]}
          />
        </Form>
      </Modal>
    </Space>
  );
}
