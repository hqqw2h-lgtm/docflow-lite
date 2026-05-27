import { PlusOutlined } from '@ant-design/icons';
import { Button, Card, Empty, Form, Input, message, Modal, Select, Space, Spin, Table, Tag, Typography } from 'antd';
import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { api } from '../api';
import { ALL_FILE_TYPES, type FileType, type SchemaSpace } from '../api/types';
import { useTenant } from '../components/TenantContext';

const STATUS_COLOR: Record<string, string> = { active: 'green', draft: 'gold', archived: 'default' };

export function SchemaSpacesPage() {
  const { tenantId } = useTenant();
  const [spaces, setSpaces] = useState<SchemaSpace[]>([]);
  const [loading, setLoading] = useState(true);
  const [open, setOpen] = useState(false);
  const [form] = Form.useForm();
  const [submitting, setSubmitting] = useState(false);

  const reload = () => {
    if (!tenantId) return;
    setLoading(true);
    api
      .listSpaces(tenantId)
      .then(setSpaces)
      .catch((e: Error) => message.error(e.message))
      .finally(() => setLoading(false));
  };

  useEffect(reload, [tenantId]);

  const onCreate = async () => {
    const values = await form.validateFields();
    setSubmitting(true);
    try {
      await api.createSpace({
        tenant_id: tenantId,
        name: values.name,
        description: values.description ?? '',
        input_file_types: values.input_file_types as FileType[],
      });
      message.success('SchemaSpace created');
      setOpen(false);
      form.resetFields();
      reload();
    } catch (e) {
      message.error((e as Error).message);
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <Card
      title={
        <Space>
          <Typography.Title level={4} style={{ margin: 0 }}>SchemaSpaces</Typography.Title>
          <Typography.Text type="secondary">
            Define an extraction scenario. Each space declares the file types it accepts and groups all versions, samples and call history.
          </Typography.Text>
        </Space>
      }
      extra={<Button type="primary" icon={<PlusOutlined />} onClick={() => setOpen(true)}>New SchemaSpace</Button>}
    >
      {loading ? (
        <Spin />
      ) : spaces.length === 0 ? (
        <Empty description="No SchemaSpaces yet" />
      ) : (
        <Table<SchemaSpace>
          rowKey="id"
          dataSource={spaces}
          pagination={false}
          columns={[
            {
              title: 'Name',
              dataIndex: 'name',
              render: (text, r) => <Link to={`/spaces/${r.id}`}>{text}</Link>,
            },
            {
              title: 'Status',
              dataIndex: 'status',
              width: 110,
              render: (s: string) => <Tag color={STATUS_COLOR[s] ?? 'default'}>{s}</Tag>,
            },
            {
              title: 'Accepts',
              dataIndex: 'input_file_types',
              render: (types: FileType[]) => (
                <Space size={4} wrap>
                  {types.map((t) => (
                    <Tag key={t}>{t}</Tag>
                  ))}
                </Space>
              ),
            },
            {
              title: 'Default model',
              render: (_, r) =>
                r.defaults.model_provider || r.defaults.model_name ? (
                  <Typography.Text code>
                    {r.defaults.model_provider || '?'}/{r.defaults.model_name || '?'}
                  </Typography.Text>
                ) : (
                  <Typography.Text type="secondary">system</Typography.Text>
                ),
            },
            {
              title: 'Updated',
              dataIndex: 'updated_at',
              width: 200,
              render: (v: string) => new Date(v).toLocaleString(),
            },
          ]}
        />
      )}

      <Modal
        title="Create SchemaSpace"
        open={open}
        onCancel={() => setOpen(false)}
        onOk={onCreate}
        confirmLoading={submitting}
        okText="Create"
      >
        <Form form={form} layout="vertical">
          <Form.Item name="name" label="Name" rules={[{ required: true, max: 80 }]}>
            <Input placeholder="e.g. Purchase orders" />
          </Form.Item>
          <Form.Item name="description" label="Description">
            <Input.TextArea rows={2} maxLength={500} placeholder="What documents this space extracts" />
          </Form.Item>
          <Form.Item
            name="input_file_types"
            label="Accepted file types"
            rules={[{ required: true, message: 'Select at least one' }]}
            tooltip="Samples and invocations are locked to these types"
          >
            <Select
              mode="multiple"
              placeholder="Select one or more"
              options={ALL_FILE_TYPES.map((t) => ({ value: t, label: t }))}
            />
          </Form.Item>
        </Form>
      </Modal>
    </Card>
  );
}
