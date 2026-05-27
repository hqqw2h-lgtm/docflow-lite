import { useEffect, useState } from 'react';
import { App as AntdApp, Button, Card, Col, Form, Input, Modal, Row, Space, Tag, Typography } from 'antd';
import { PlusOutlined } from '@ant-design/icons';
import { useNavigate } from 'react-router-dom';
import { tenantsApi } from '../../shared/api';
import { useTenants } from '../../shared/hooks/TenantContext';

export function TenantCenterPage() {
  const { tenants, refresh, setTenantId } = useTenants();
  const [open, setOpen] = useState(false);
  const [form] = Form.useForm<{ name: string; description: string }>();
  const [submitting, setSubmitting] = useState(false);
  const { message } = AntdApp.useApp();
  const navigate = useNavigate();

  useEffect(() => {
    void refresh();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const submit = async () => {
    try {
      const values = await form.validateFields();
      setSubmitting(true);
      const tenant = await tenantsApi.create(values);
      message.success(`Tenant ${tenant.name} created.`);
      form.resetFields();
      setOpen(false);
      await refresh();
      setTenantId(tenant.id);
    } catch (error) {
      if ((error as Error).message) message.error((error as Error).message);
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <>
      <Space style={{ marginBottom: 16, justifyContent: 'space-between', width: '100%' }}>
        <Typography.Title level={3} style={{ margin: 0 }}>
          Tenants
        </Typography.Title>
        <Button type="primary" icon={<PlusOutlined />} onClick={() => setOpen(true)}>
          New tenant
        </Button>
      </Space>
      <Row gutter={[16, 16]}>
        {tenants.map((tenant) => (
          <Col xs={24} sm={12} lg={8} xxl={6} key={tenant.id}>
            <Card
              hoverable
              title={
                <Space>
                  {tenant.name}
                  <Tag color={tenant.status === 'active' ? 'green' : 'default'}>{tenant.status}</Tag>
                </Space>
              }
              onClick={() => {
                setTenantId(tenant.id);
                navigate('/workspaces');
              }}
            >
              <Typography.Paragraph type="secondary" ellipsis={{ rows: 3 }}>
                {tenant.description || 'No description.'}
              </Typography.Paragraph>
              <Typography.Text type="secondary" style={{ fontSize: 12 }}>
                Updated {new Date(tenant.updated_at).toLocaleString()}
              </Typography.Text>
            </Card>
          </Col>
        ))}
        {tenants.length === 0 && (
          <Col span={24}>
            <Card>
              <Typography.Text type="secondary">
                No tenants yet. Create your first tenant to start adding workspaces.
              </Typography.Text>
            </Card>
          </Col>
        )}
      </Row>
      <Modal
        title="Create tenant"
        open={open}
        onCancel={() => setOpen(false)}
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
            <Input placeholder="e.g. Procurement" autoFocus />
          </Form.Item>
          <Form.Item name="description" label="Description">
            <Input.TextArea rows={3} placeholder="What does this tenant own?" />
          </Form.Item>
        </Form>
      </Modal>
    </>
  );
}
