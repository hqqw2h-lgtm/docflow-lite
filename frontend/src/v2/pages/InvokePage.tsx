import { PlayCircleOutlined, UploadOutlined } from '@ant-design/icons';
import { Alert, Button, Card, Descriptions, Form, Input, message, Space, Spin, Tag, Typography, Upload } from 'antd';
import type { UploadFile } from 'antd/es/upload/interface';
import { useEffect, useState } from 'react';
import { Link, useParams } from 'react-router-dom';
import { api } from '../api';
import type { Invocation, SchemaSpace, SchemaSpaceVersion } from '../api/types';
import { JsonView } from '../components/JsonView';
import { TraceDrawer } from '../components/TraceDrawer';

export function InvokePage() {
  const { spaceId = '', versionId = '' } = useParams();
  const [space, setSpace] = useState<SchemaSpace | null>(null);
  const [version, setVersion] = useState<SchemaSpaceVersion | null>(null);
  const [file, setFile] = useState<UploadFile | null>(null);
  const [context, setContext] = useState('');
  const [running, setRunning] = useState(false);
  const [last, setLast] = useState<Invocation | null>(null);
  const [traceOpen, setTraceOpen] = useState<Invocation | null>(null);

  useEffect(() => {
    Promise.all([api.getSpace(spaceId), api.getVersion(spaceId, versionId)])
      .then(([s, v]) => { setSpace(s); setVersion(v); })
      .catch((e: Error) => message.error(e.message));
  }, [spaceId, versionId]);

  if (!space || !version) return <Spin />;

  const onRun = async () => {
    if (!file?.originFileObj) { message.error('Choose a file'); return; }
    setRunning(true);
    try {
      const inv = await api.invoke(spaceId, versionId, file.originFileObj as File, context);
      setLast(inv);
      message.success(`Invocation ${inv.status}`);
    } catch (e) { message.error((e as Error).message); }
    finally { setRunning(false); }
  };

  return (
    <Space direction="vertical" size={16} style={{ width: '100%' }}>
      <Card
        title={
          <Space>
            <Link to="/spaces"><Typography.Text type="secondary">SchemaSpaces</Typography.Text></Link>
            <Typography.Text type="secondary">/</Typography.Text>
            <Link to={`/spaces/${spaceId}`}><Typography.Text type="secondary">{space.name}</Typography.Text></Link>
            <Typography.Text type="secondary">/</Typography.Text>
            <Link to={`/spaces/${spaceId}/versions/${versionId}`}><Typography.Text type="secondary">v{version.version}</Typography.Text></Link>
            <Typography.Text type="secondary">/</Typography.Text>
            <Typography.Title level={4} style={{ margin: 0 }}>Invoke</Typography.Title>
          </Space>
        }
      >
        {version.status !== 'published' ? (
          <Alert type="warning" showIcon message="Only published versions can be invoked. Publish first." />
        ) : (
          <>
            <Descriptions size="small" column={3} style={{ marginBottom: 16 }}>
              <Descriptions.Item label="Accepted">{space.input_file_types.map((t) => <Tag key={t}>{t}</Tag>)}</Descriptions.Item>
              <Descriptions.Item label="Model">{version.model_provider || space.defaults.model_provider || 'system'} / {version.model_name || space.defaults.model_name || 'system'}</Descriptions.Item>
            </Descriptions>
            <Form layout="vertical">
              <Form.Item label="Document" required>
                <Upload
                  maxCount={1}
                  beforeUpload={(f) => { setFile({ uid: f.uid, name: f.name, originFileObj: f } as UploadFile); return false; }}
                  onRemove={() => setFile(null)}
                  fileList={file ? [file] : []}
                >
                  <Button icon={<UploadOutlined />}>Choose file</Button>
                </Upload>
              </Form.Item>
              <Form.Item label="Document context (optional)">
                <Input.TextArea rows={2} value={context} onChange={(e) => setContext(e.target.value)} />
              </Form.Item>
              <Button type="primary" icon={<PlayCircleOutlined />} loading={running} onClick={onRun}>Run</Button>
            </Form>
          </>
        )}
      </Card>

      {last ? (
        <Card title={<Typography.Title level={5} style={{ margin: 0 }}>Result</Typography.Title>}
          extra={<Button onClick={() => setTraceOpen(last)}>Show full trace</Button>}>
          <Descriptions size="small" column={3} style={{ marginBottom: 12 }}>
            <Descriptions.Item label="Status"><Tag>{last.status}</Tag></Descriptions.Item>
            <Descriptions.Item label="Duration">{last.duration_ms} ms</Descriptions.Item>
            <Descriptions.Item label="Invocation ID">{last.id}</Descriptions.Item>
          </Descriptions>
          {last.error_message ? (
            <Alert type="error" showIcon style={{ marginBottom: 12 }} message={`[${last.error_code}] ${last.error_message}`} />
          ) : null}
          <Typography.Title level={5}>Output</Typography.Title>
          <JsonView value={last.final_output} />
          {last.validation_issues?.length ? (
            <>
              <Typography.Title level={5}>Validation issues</Typography.Title>
              <JsonView value={last.validation_issues} maxHeight={200} />
            </>
          ) : null}
        </Card>
      ) : null}

      <TraceDrawer invocation={traceOpen} onClose={() => setTraceOpen(null)} />
    </Space>
  );
}
