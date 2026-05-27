import { useEffect, useMemo, useState } from 'react';
import {
  App as AntdApp,
  Button,
  Card,
  Col,
  Empty,
  Form,
  Input,
  Modal,
  Row,
  Segmented,
  Space,
  Tag,
  Typography
} from 'antd';
import { PlusOutlined, SearchOutlined } from '@ant-design/icons';
import { useNavigate } from 'react-router-dom';
import { workspacesApi } from '../../shared/api';
import { useTenants } from '../../shared/hooks/TenantContext';
import type { Workspace } from '../../shared/types';

type ActiveFilter = 'all' | 'true' | 'false';

export function WorkspaceListPage() {
  const { tenantId, selectedTenant, tenants } = useTenants();
  const navigate = useNavigate();
  const { message } = AntdApp.useApp();
  const [workspaces, setWorkspaces] = useState<Workspace[]>([]);
  const [query, setQuery] = useState('');
  const [activeFilter, setActiveFilter] = useState<ActiveFilter>('all');
  const [createOpen, setCreateOpen] = useState(false);
  const [form] = Form.useForm<{ name: string; description: string }>();
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    if (!tenantId) {
      setWorkspaces([]);
      return;
    }
    void workspacesApi
      .list({
        tenantId,
        query,
        active: activeFilter === 'all' ? '' : activeFilter
      })
      .then(setWorkspaces)
      .catch((error: Error) => message.error(error.message));
  }, [tenantId, query, activeFilter, message]);

  const stats = useMemo(
    () => ({
      total: workspaces.length,
      active: workspaces.filter((item) => item.active_status).length,
      inactive: workspaces.filter((item) => !item.active_status).length
    }),
    [workspaces]
  );

  const submit = async () => {
    if (!tenantId) {
      message.warning('Please select a tenant first.');
      return;
    }
    try {
      const values = await form.validateFields();
      setSubmitting(true);
      const workspace = await workspacesApi.create({ tenant_id: tenantId, ...values });
      message.success(`Workspace ${workspace.name} created.`);
      form.resetFields();
      setCreateOpen(false);
      setWorkspaces((prev) => [workspace, ...prev]);
      navigate(`/workspaces/${workspace.id}/initialization/output`);
    } catch (error) {
      if ((error as Error).message) message.error((error as Error).message);
    } finally {
      setSubmitting(false);
    }
  };

  if (!tenants.length) {
    return (
      <Empty
        description="No tenants yet. Create a tenant first."
        style={{ background: '#fff', padding: 48, borderRadius: 8 }}
      >
        <Button type="primary" onClick={() => navigate('/tenants')}>
          Go to tenants
        </Button>
      </Empty>
    );
  }

  return (
    <>
      <Space style={{ marginBottom: 16, justifyContent: 'space-between', width: '100%' }} align="center">
        <Space direction="vertical" size={0}>
          <Typography.Title level={3} style={{ margin: 0 }}>
            Workspaces
          </Typography.Title>
          <Typography.Text type="secondary">
            Tenant: {selectedTenant?.name ?? '—'} · {stats.total} total · {stats.active} active ·{' '}
            {stats.inactive} inactive
          </Typography.Text>
        </Space>
        <Space>
          <Input
            allowClear
            prefix={<SearchOutlined />}
            placeholder="Search workspace"
            value={query}
            onChange={(event) => setQuery(event.target.value)}
            style={{ width: 240 }}
          />
          <Segmented
            value={activeFilter}
            onChange={(value) => setActiveFilter(value as ActiveFilter)}
            options={[
              { label: 'All', value: 'all' },
              { label: 'Active', value: 'true' },
              { label: 'Inactive', value: 'false' }
            ]}
          />
          <Button type="primary" icon={<PlusOutlined />} onClick={() => setCreateOpen(true)}>
            New workspace
          </Button>
        </Space>
      </Space>
      <Row gutter={[16, 16]}>
        {workspaces.map((workspace) => (
          <Col xs={24} sm={12} lg={8} xxl={6} key={workspace.id}>
            <Card
              hoverable
              title={
                <Space>
                  {workspace.name}
                  <Tag color={workspace.active_status ? 'green' : 'default'}>
                    {workspace.active_status ? 'Active' : 'Inactive'}
                  </Tag>
                </Space>
              }
              onClick={() => navigate(`/workspaces/${workspace.id}/initialization/output`)}
            >
              <Typography.Paragraph type="secondary" ellipsis={{ rows: 3 }}>
                {workspace.description || 'No description.'}
              </Typography.Paragraph>
              <Space size={[6, 6]} wrap>
                <Tag>{workspace.schema_type.replaceAll('_', ' ').toLowerCase()}</Tag>
                <Tag color={workspace.initialization_status === 'active' ? 'blue' : 'default'}>
                  init: {workspace.initialization_status}
                </Tag>
              </Space>
              <Typography.Paragraph type="secondary" style={{ marginTop: 12, marginBottom: 0, fontSize: 12 }}>
                Updated {new Date(workspace.updated_at).toLocaleString()}
              </Typography.Paragraph>
            </Card>
          </Col>
        ))}
        {workspaces.length === 0 && (
          <Col span={24}>
            <Card>
              <Empty description="No workspaces match the current filter." />
            </Card>
          </Col>
        )}
      </Row>
      <Modal
        title="Create workspace"
        open={createOpen}
        onCancel={() => setCreateOpen(false)}
        onOk={submit}
        confirmLoading={submitting}
        okText="Create"
      >
        <Form form={form} layout="vertical">
          <Form.Item
            name="name"
            label="Name"
            rules={[{ required: true, message: 'Name is required' }]}
          >
            <Input placeholder="e.g. Purchase orders" autoFocus />
          </Form.Item>
          <Form.Item name="description" label="Description">
            <Input.TextArea rows={3} placeholder="What documents does this workspace handle?" />
          </Form.Item>
        </Form>
      </Modal>
    </>
  );
}
