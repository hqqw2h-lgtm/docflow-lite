import { Breadcrumb, Layout, Menu, Skeleton, Space, Tag, Typography } from 'antd';
import {
  ApiOutlined,
  ArrowLeftOutlined,
  BranchesOutlined,
  ControlOutlined,
  DatabaseOutlined,
  FileSearchOutlined,
  FormOutlined,
  ThunderboltOutlined
} from '@ant-design/icons';
import { Link, Outlet, useLocation, useParams } from 'react-router-dom';
import { useWorkspace } from '../hooks/useWorkspace';
import type { Workspace } from '../types';

export interface WorkspaceOutletContext {
  workspace: Workspace | null;
  setWorkspace: (workspace: Workspace | null) => void;
}

const { Sider, Content } = Layout;

function buildMenu(workspaceId: string) {
  return [
    {
      key: 'initialization',
      icon: <FormOutlined />,
      label: 'Initialization',
      children: [
        {
          key: `/workspaces/${workspaceId}/initialization/output`,
          label: <Link to={`/workspaces/${workspaceId}/initialization/output`}>Expected Output</Link>
        },
        {
          key: `/workspaces/${workspaceId}/initialization/validation`,
          label: <Link to={`/workspaces/${workspaceId}/initialization/validation`}>Validation</Link>
        }
      ]
    },
    {
      key: `/workspaces/${workspaceId}/samples`,
      icon: <DatabaseOutlined />,
      label: <Link to={`/workspaces/${workspaceId}/samples`}>Samples</Link>
    },
    {
      key: `/workspaces/${workspaceId}/prompt-versions`,
      icon: <BranchesOutlined />,
      label: <Link to={`/workspaces/${workspaceId}/prompt-versions`}>Prompt Versions</Link>
    },
    {
      key: `/workspaces/${workspaceId}/extracted-result`,
      icon: <FileSearchOutlined />,
      label: <Link to={`/workspaces/${workspaceId}/extracted-result`}>Extracted Result</Link>
    },
    {
      key: `/workspaces/${workspaceId}/integration`,
      icon: <ThunderboltOutlined />,
      label: <Link to={`/workspaces/${workspaceId}/integration`}>Integration</Link>
    },
    {
      key: `/workspaces/${workspaceId}/api-access`,
      icon: <ApiOutlined />,
      label: <Link to={`/workspaces/${workspaceId}/api-access`}>API Access</Link>
    },
    {
      key: `/workspaces/${workspaceId}/settings/processing`,
      icon: <ControlOutlined />,
      label: <Link to={`/workspaces/${workspaceId}/settings/processing`}>Processing Settings</Link>
    }
  ];
}

export function WorkspaceShell() {
  const { workspaceId = '' } = useParams<{ workspaceId: string }>();
  const location = useLocation();
  const { workspace, setWorkspace, loading } = useWorkspace(workspaceId);

  const items = buildMenu(workspaceId);

  const selectedKey = location.pathname;
  const openKey = location.pathname.includes('/initialization/') ? 'initialization' : '';

  return (
    <Layout style={{ background: '#f5f6f8', minHeight: 'calc(100vh - 64px)' }}>
      <Sider
        theme="light"
        width={232}
        style={{ borderRight: '1px solid #f0f0f0' }}
      >
        <div style={{ padding: '16px 16px 8px' }}>
          <Link to="/workspaces" style={{ display: 'inline-flex', alignItems: 'center', gap: 6, color: 'rgba(0,0,0,0.65)' }}>
            <ArrowLeftOutlined /> All workspaces
          </Link>
        </div>
        <Menu
          mode="inline"
          selectedKeys={[selectedKey]}
          defaultOpenKeys={[openKey].filter(Boolean)}
          items={items}
          style={{ borderRight: 'none' }}
        />
      </Sider>
      <Content style={{ padding: 24 }}>
        <Space direction="vertical" size={4} style={{ marginBottom: 16, width: '100%' }}>
          <Breadcrumb
            items={[
              { title: <Link to="/workspaces">Workspaces</Link> },
              { title: workspace?.name ?? workspaceId }
            ]}
          />
          {loading && !workspace ? (
            <Skeleton active paragraph={{ rows: 1 }} title={{ width: 240 }} />
          ) : workspace ? (
            <Space size={12} align="center">
              <Typography.Title level={3} style={{ margin: 0 }}>
                {workspace.name}
              </Typography.Title>
              <Tag color={workspace.active_status ? 'green' : 'default'}>
                {workspace.active_status ? 'Active' : 'Inactive'}
              </Tag>
              <Tag color={workspace.initialization_status === 'active' ? 'blue' : 'default'}>
                {workspace.initialization_status === 'active'
                  ? 'Initialization completed'
                  : 'Initialization in progress'}
              </Tag>
              {workspace.description && (
                <Typography.Text type="secondary">{workspace.description}</Typography.Text>
              )}
            </Space>
          ) : null}
        </Space>
        <Outlet context={{ workspace, setWorkspace }} />
      </Content>
    </Layout>
  );
}
