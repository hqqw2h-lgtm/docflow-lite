import { ConfigProvider, App as AntdApp } from 'antd';
import { createHashRouter, Navigate, RouterProvider } from 'react-router-dom';
import { AppShell } from './components/AppShell';
import { TenantProvider } from './components/TenantContext';
import { AdminInvocationsPage } from './pages/AdminInvocationsPage';
import { InvokePage } from './pages/InvokePage';
import { SchemaSpaceDetailPage } from './pages/SchemaSpaceDetailPage';
import { SchemaSpacesPage } from './pages/SchemaSpacesPage';
import { VersionDetailPage } from './pages/VersionDetailPage';

const router = createHashRouter([
  {
    path: '/',
    element: <AppShell />,
    children: [
      { index: true, element: <Navigate to="/spaces" replace /> },
      { path: 'spaces', element: <SchemaSpacesPage /> },
      { path: 'spaces/:spaceId', element: <SchemaSpaceDetailPage /> },
      { path: 'spaces/:spaceId/versions/:versionId', element: <VersionDetailPage /> },
      { path: 'spaces/:spaceId/versions/:versionId/invoke', element: <InvokePage /> },
      { path: 'invocations', element: <AdminInvocationsPage admin={false} /> },
      { path: 'admin/traces', element: <AdminInvocationsPage admin /> },
      { path: '*', element: <Navigate to="/spaces" replace /> },
    ],
  },
]);

export default function App() {
  return (
    <ConfigProvider theme={{ token: { colorPrimary: '#3b6cf5', borderRadius: 6 } }}>
      <AntdApp>
        <TenantProvider>
          <RouterProvider router={router} />
        </TenantProvider>
      </AntdApp>
    </ConfigProvider>
  );
}
