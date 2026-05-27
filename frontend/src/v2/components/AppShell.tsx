import { ApiOutlined, AppstoreOutlined, AuditOutlined } from '@ant-design/icons';
import { Layout, Menu, Select, Typography } from 'antd';
import { Link, Outlet, useLocation } from 'react-router-dom';
import { useTenant } from './TenantContext';

const { Header, Sider, Content } = Layout;
const { Title } = Typography;

const MENU = [
  { key: '/spaces', icon: <AppstoreOutlined />, label: <Link to="/spaces">SchemaSpaces</Link> },
  { key: '/invocations', icon: <ApiOutlined />, label: <Link to="/invocations">Invocations</Link> },
  { key: '/admin/traces', icon: <AuditOutlined />, label: <Link to="/admin/traces">Admin · Traces</Link> },
];

export function AppShell() {
  const { tenants, tenantId, setTenantId, loading } = useTenant();
  const location = useLocation();
  const activeKey =
    MENU.find((m) => location.pathname.startsWith(m.key))?.key ?? '/spaces';

  return (
    <Layout style={{ minHeight: '100vh' }}>
      <Sider theme="light" width={220} style={{ borderRight: '1px solid #f0f0f0' }}>
        <div style={{ padding: 20, borderBottom: '1px solid #f0f0f0' }}>
          <Title level={4} style={{ margin: 0 }}>DocFlow</Title>
          <Typography.Text type="secondary" style={{ fontSize: 12 }}>SchemaSpace Console</Typography.Text>
        </div>
        <Menu mode="inline" selectedKeys={[activeKey]} items={MENU} style={{ borderInlineEnd: 0 }} />
      </Sider>
      <Layout>
        <Header style={{ background: '#fff', borderBottom: '1px solid #f0f0f0', display: 'flex', alignItems: 'center', justifyContent: 'space-between', paddingInline: 24 }}>
          <Typography.Text type="secondary">Tenant</Typography.Text>
          <Select
            loading={loading}
            value={tenantId || undefined}
            style={{ minWidth: 240 }}
            placeholder="Select tenant"
            options={tenants.map((t) => ({ label: t.name, value: t.id }))}
            onChange={setTenantId}
          />
        </Header>
        <Content style={{ padding: 24, background: '#f5f5f5' }}>
          <Outlet />
        </Content>
      </Layout>
    </Layout>
  );
}
