import { Layout, Menu, Select, Space, Typography } from 'antd';
import { ApartmentOutlined, AppstoreOutlined, SettingOutlined } from '@ant-design/icons';
import { Link, Outlet, useLocation, useNavigate } from 'react-router-dom';
import { useTenants } from '../hooks/TenantContext';

const { Header, Content } = Layout;

const items = [
  {
    key: 'tenants',
    icon: <ApartmentOutlined />,
    label: <Link to="/tenants">Tenants</Link>
  },
  {
    key: 'workspaces',
    icon: <AppstoreOutlined />,
    label: <Link to="/workspaces">Workspaces</Link>
  },
  {
    key: 'settings',
    icon: <SettingOutlined />,
    label: <Link to="/settings/models">Model Settings</Link>
  }
];

function resolveActiveKey(pathname: string): string {
  if (pathname.startsWith('/tenants')) return 'tenants';
  if (pathname.startsWith('/settings')) return 'settings';
  return 'workspaces';
}

export function AppShell() {
  const { tenants, tenantId, setTenantId } = useTenants();
  const location = useLocation();
  const navigate = useNavigate();
  const activeKey = resolveActiveKey(location.pathname);

  return (
    <Layout style={{ minHeight: '100vh' }}>
      <Header
        style={{
          display: 'flex',
          alignItems: 'center',
          gap: 24,
          background: '#fff',
          borderBottom: '1px solid #f0f0f0',
          paddingInline: 24
        }}
      >
        <Space size={12} align="center" style={{ marginRight: 24 }}>
          <Typography.Title level={4} style={{ margin: 0 }}>
            DocFlow Lite
          </Typography.Title>
        </Space>
        <Menu
          mode="horizontal"
          selectedKeys={[activeKey]}
          items={items}
          style={{ flex: 1, minWidth: 0, borderBottom: 'none' }}
        />
        <Space>
          <span style={{ color: 'rgba(0,0,0,0.45)' }}>Tenant</span>
          <Select
            value={tenantId || undefined}
            placeholder="Select tenant"
            style={{ minWidth: 200 }}
            onChange={(value) => {
              setTenantId(value);
              if (activeKey === 'workspaces') {
                navigate('/workspaces');
              }
            }}
            options={tenants.map((tenant) => ({ value: tenant.id, label: tenant.name }))}
          />
        </Space>
      </Header>
      <Content style={{ padding: 24, background: '#f5f6f8' }}>
        <Outlet />
      </Content>
    </Layout>
  );
}
