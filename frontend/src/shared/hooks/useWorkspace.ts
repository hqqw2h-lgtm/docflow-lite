import { useEffect, useState } from 'react';
import { App as AntdApp } from 'antd';
import { workspacesApi } from '../api';
import type { Workspace } from '../types';

export function useWorkspace(workspaceId: string | undefined) {
  const [workspace, setWorkspace] = useState<Workspace | null>(null);
  const [loading, setLoading] = useState(false);
  const [refreshKey, setRefreshKey] = useState(0);
  const { message } = AntdApp.useApp();

  useEffect(() => {
    if (!workspaceId) {
      setWorkspace(null);
      return;
    }
    let cancelled = false;
    setLoading(true);
    workspacesApi
      .get(workspaceId)
      .then((data) => {
        if (!cancelled) setWorkspace(data);
      })
      .catch((error: Error) => {
        if (!cancelled) message.error(error.message);
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [workspaceId, refreshKey, message]);

  return {
    workspace,
    setWorkspace,
    loading,
    refresh: () => setRefreshKey((value) => value + 1)
  };
}
