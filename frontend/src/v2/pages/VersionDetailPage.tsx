import {
  CheckCircleOutlined, CloseCircleOutlined, CopyOutlined, ExperimentOutlined, RocketOutlined, UploadOutlined,
} from '@ant-design/icons';
import {
  Alert, Button, Card, Descriptions, Divider, Empty, Form, Input, message, Modal, Popconfirm, Space, Spin,
  Table, Tabs, Tag, Tooltip, Typography, Upload,
} from 'antd';
import type { UploadFile } from 'antd/es/upload/interface';
import { useEffect, useMemo, useState } from 'react';
import { Link, useNavigate, useParams } from 'react-router-dom';
import { api } from '../api';
import type {
  OptimizationReport, Sample, SchemaSpace, SchemaSpaceVersion,
} from '../api/types';
import { JsonView } from '../components/JsonView';

const VER_COLOR: Record<string, string> = { draft: 'gold', published: 'green', archived: 'default' };
const SAMPLE_COLOR: Record<string, string> = {
  uploaded: 'blue', extracted: 'cyan', confirmed: 'green', rejected: 'red', needs_review: 'orange',
};

export function VersionDetailPage() {
  const { spaceId = '', versionId = '' } = useParams();
  const nav = useNavigate();
  const [space, setSpace] = useState<SchemaSpace | null>(null);
  const [version, setVersion] = useState<SchemaSpaceVersion | null>(null);
  const [samples, setSamples] = useState<Sample[]>([]);
  const [loading, setLoading] = useState(true);
  const [uploadOpen, setUploadOpen] = useState(false);
  const [uploadForm] = Form.useForm();
  const [uploadFile, setUploadFile] = useState<UploadFile | null>(null);
  const [uploading, setUploading] = useState(false);
  const [schemaOpen, setSchemaOpen] = useState(false);
  const [schemaText, setSchemaText] = useState('');
  const [optReport, setOptReport] = useState<OptimizationReport | null>(null);
  const [optimizing, setOptimizing] = useState(false);

  const reload = () => {
    setLoading(true);
    Promise.all([
      api.getSpace(spaceId),
      api.getVersion(spaceId, versionId),
      api.listSamples(spaceId, versionId),
      api.lastOptimization(spaceId, versionId).then((r) => r.report).catch(() => null),
    ])
      .then(([s, v, ss, opt]) => {
        setSpace(s);
        setVersion(v);
        setSamples(ss);
        setOptReport(opt);
      })
      .catch((e: Error) => message.error(e.message))
      .finally(() => setLoading(false));
  };

  useEffect(() => { if (spaceId && versionId) reload(); }, [spaceId, versionId]);

  const acceptHint = useMemo(() => {
    if (!space) return '';
    const exts: Record<string, string> = {
      pdf: '.pdf', excel: '.xlsx,.xls,.xlsm', csv: '.csv', text: '.txt,.log',
      json: '.json', image: '.png,.jpg,.jpeg,.tif,.tiff', markdown: '.md,.markdown',
    };
    return space.input_file_types.map((t) => exts[t] ?? '').filter(Boolean).join(',');
  }, [space]);

  if (loading || !space || !version) return <Spin />;

  const isDraft = version.status === 'draft';
  const isPublished = version.status === 'published';

  const onUpload = async () => {
    const values = await uploadForm.validateFields();
    if (!uploadFile?.originFileObj) {
      message.error('Choose a file');
      return;
    }
    setUploading(true);
    try {
      await api.uploadSample(
        spaceId, versionId,
        uploadFile.originFileObj as File,
        values.expected_output ?? '',
        values.document_context ?? '',
      );
      message.success('Sample uploaded');
      setUploadOpen(false);
      uploadForm.resetFields();
      setUploadFile(null);
      reload();
    } catch (e) {
      message.error((e as Error).message);
    } finally {
      setUploading(false);
    }
  };

  const onSaveSchema = async () => {
    let parsed: unknown;
    try { parsed = JSON.parse(schemaText); }
    catch { message.error('Invalid JSON'); return; }
    try {
      await api.updateVersion(spaceId, versionId, { schema_info: parsed });
      message.success('Schema saved');
      setSchemaOpen(false);
      reload();
    } catch (e) { message.error((e as Error).message); }
  };

  const onOptimize = async (apply: boolean) => {
    setOptimizing(true);
    try {
      const report = await api.runOptimizer(spaceId, versionId, apply);
      setOptReport(report);
      message.success(apply ? 'Optimizer applied best combination' : 'Optimizer report ready (preview only)');
    } catch (e) { message.error((e as Error).message); }
    finally { setOptimizing(false); }
  };

  const onPublish = async () => {
    try {
      await api.publishVersion(spaceId, versionId);
      message.success('Published');
      reload();
    } catch (e) { message.error((e as Error).message); }
  };

  const onClone = async () => {
    try {
      const v = await api.cloneVersion(spaceId, versionId);
      message.success(`Cloned as v${v.version}`);
      nav(`/spaces/${spaceId}/versions/${v.id}`);
    } catch (e) { message.error((e as Error).message); }
  };

  const onArchive = async () => {
    try {
      await api.archiveVersion(spaceId, versionId);
      message.success('Archived');
      reload();
    } catch (e) { message.error((e as Error).message); }
  };

  const confirmedCount = samples.filter((s) => s.status === 'confirmed').length;

  return (
    <Space direction="vertical" size={16} style={{ width: '100%' }}>
      <Card
        title={
          <Space>
            <Link to="/spaces"><Typography.Text type="secondary">SchemaSpaces</Typography.Text></Link>
            <Typography.Text type="secondary">/</Typography.Text>
            <Link to={`/spaces/${spaceId}`}><Typography.Text type="secondary">{space.name}</Typography.Text></Link>
            <Typography.Text type="secondary">/</Typography.Text>
            <Typography.Title level={4} style={{ margin: 0 }}>v{version.version}</Typography.Title>
            <Tag color={VER_COLOR[version.status] ?? 'default'}>{version.status}</Tag>
          </Space>
        }
        extra={
          <Space>
            {isPublished ? (
              <Button type="primary" icon={<RocketOutlined />} onClick={() => nav(`/spaces/${spaceId}/versions/${versionId}/invoke`)}>
                Invoke
              </Button>
            ) : null}
            <Button icon={<CopyOutlined />} onClick={onClone}>Clone</Button>
            {isDraft ? (
              <Tooltip title={confirmedCount === 0 ? 'Need at least 1 confirmed sample' : 'Lock this version and start serving'}>
                <Popconfirm
                  title="Publish this version?"
                  description="Published versions become immutable. Clone to make further changes."
                  onConfirm={onPublish}
                  disabled={confirmedCount === 0}
                >
                  <Button type="primary" disabled={confirmedCount === 0}>Publish</Button>
                </Popconfirm>
              </Tooltip>
            ) : null}
            {version.status !== 'archived' ? (
              <Popconfirm title="Archive this version?" onConfirm={onArchive}>
                <Button danger>Archive</Button>
              </Popconfirm>
            ) : null}
          </Space>
        }
      >
        <Descriptions size="small" column={3}>
          <Descriptions.Item label="Version ID">{version.id}</Descriptions.Item>
          <Descriptions.Item label="Samples">{version.sample_count}</Descriptions.Item>
          <Descriptions.Item label="Model override">
            {version.model_provider ? `${version.model_provider}/${version.model_name}` : 'inherits'}
          </Descriptions.Item>
          <Descriptions.Item label="Parent">{version.parent_version_id || '-'}</Descriptions.Item>
          <Descriptions.Item label="Published">{version.published_at ? new Date(version.published_at).toLocaleString() : '-'}</Descriptions.Item>
          <Descriptions.Item label="Updated">{new Date(version.updated_at).toLocaleString()}</Descriptions.Item>
        </Descriptions>
      </Card>

      <Tabs
        items={[
          {
            key: 'samples',
            label: `Samples (${samples.length})`,
            children: (
              <Card
                size="small"
                extra={isDraft ? (
                  <Button type="primary" icon={<UploadOutlined />} onClick={() => setUploadOpen(true)}>Upload sample</Button>
                ) : (
                  <Tooltip title="Clone this version to upload more samples"><Button disabled icon={<UploadOutlined />}>Upload sample</Button></Tooltip>
                )}
              >
                {samples.length === 0 ? (
                  <Empty description="No samples. Upload at least one to publish." />
                ) : (
                  <Table<Sample>
                    rowKey="id"
                    dataSource={samples}
                    pagination={false}
                    expandable={{
                      expandedRowRender: (s) => (
                        <Space direction="vertical" style={{ width: '100%' }}>
                          {s.document_context ? (
                            <Alert type="info" message="Document context" description={s.document_context} />
                          ) : null}
                          <Typography.Text strong>Expected:</Typography.Text>
                          <JsonView value={s.expected_output} maxHeight={180} />
                          <Typography.Text strong>Model output:</Typography.Text>
                          <JsonView value={s.model_output} maxHeight={180} />
                        </Space>
                      ),
                    }}
                    columns={[
                      { title: 'File', dataIndex: 'file_name' },
                      { title: 'Type', dataIndex: 'file_type', width: 90, render: (t: string) => <Tag>{t}</Tag> },
                      { title: 'Size', dataIndex: 'size_bytes', width: 110, render: (n: number) => `${n} B` },
                      { title: 'Status', dataIndex: 'status', width: 130, render: (s: string) => <Tag color={SAMPLE_COLOR[s] ?? 'default'}>{s}</Tag> },
                      {
                        title: 'Actions',
                        width: 220,
                        render: (_, s) => isDraft ? (
                          <Space>
                            <Button size="small" type="primary" icon={<CheckCircleOutlined />}
                              disabled={s.status === 'confirmed'}
                              onClick={async () => {
                                try { await api.confirmSample(spaceId, versionId, s.id); message.success('Confirmed'); reload(); }
                                catch (e) { message.error((e as Error).message); }
                              }}
                            >Confirm</Button>
                            <Button size="small" danger icon={<CloseCircleOutlined />}
                              disabled={s.status === 'rejected'}
                              onClick={async () => {
                                try { await api.rejectSample(spaceId, versionId, s.id); message.success('Rejected'); reload(); }
                                catch (e) { message.error((e as Error).message); }
                              }}
                            >Reject</Button>
                          </Space>
                        ) : <Typography.Text type="secondary">read-only</Typography.Text>,
                      },
                    ]}
                  />
                )}
              </Card>
            ),
          },
          {
            key: 'schema',
            label: 'Schema',
            children: (
              <Card
                size="small"
                extra={isDraft ? (
                  <Button onClick={() => { setSchemaText(JSON.stringify(version.schema_info ?? {}, null, 2)); setSchemaOpen(true); }}>
                    Edit schema
                  </Button>
                ) : null}
              >
                <Typography.Paragraph type="secondary">
                  The expected output JSON structure. Samples must match this shape.
                </Typography.Paragraph>
                <JsonView value={version.schema_info} maxHeight={420} />
              </Card>
            ),
          },
          {
            key: 'optimizer',
            label: 'Optimizer',
            children: (
              <Card
                size="small"
                extra={isDraft ? (
                  <Space>
                    <Button onClick={() => onOptimize(false)} loading={optimizing}>Preview</Button>
                    <Button type="primary" icon={<ExperimentOutlined />}
                      onClick={() => onOptimize(true)} loading={optimizing}
                      disabled={confirmedCount === 0}
                    >Run & apply</Button>
                  </Space>
                ) : null}
              >
                <Alert
                  type="info" showIcon style={{ marginBottom: 12 }}
                  message="Before publishing, the optimizer grid-searches normalizer combinations against confirmed samples and applies the best one. You don't have to pick normalizers manually."
                />
                {!optReport ? (
                  <Empty description="No optimizer report yet. Confirm samples then click Run & apply." />
                ) : (
                  <>
                    <Descriptions size="small" column={3} bordered style={{ marginBottom: 12 }}>
                      <Descriptions.Item label="Best score">{optReport.best_score.toFixed(3)}</Descriptions.Item>
                      <Descriptions.Item label="Applied">{optReport.applied ? 'Yes' : 'No'}</Descriptions.Item>
                      <Descriptions.Item label="Trials">{optReport.trials.length}</Descriptions.Item>
                      <Descriptions.Item label="Winning normalizers" span={3}>
                        {Object.entries(optReport.best_combination).length === 0
                          ? <Typography.Text type="secondary">defaults</Typography.Text>
                          : Object.entries(optReport.best_combination).map(([k, v]) => <Tag key={k}>{k}: {v}</Tag>)}
                      </Descriptions.Item>
                    </Descriptions>
                    <Table
                      size="small"
                      rowKey={(r, i) => String(i)}
                      dataSource={optReport.trials}
                      pagination={false}
                      columns={[
                        {
                          title: 'Combination',
                          render: (_, r) => Object.entries(r.overrides).length === 0
                            ? <Tag>defaults</Tag>
                            : Object.entries(r.overrides).map(([k, v]) => <Tag key={k}>{k}: {v}</Tag>),
                        },
                        { title: 'Avg score', dataIndex: 'avg_score', width: 110, render: (v: number) => v.toFixed(3) },
                        { title: 'Errors', dataIndex: 'error_count', width: 80 },
                        { title: 'Samples', dataIndex: 'sample_count', width: 90 },
                      ]}
                    />
                  </>
                )}
              </Card>
            ),
          },
        ]}
      />

      <Modal
        title="Upload sample"
        open={uploadOpen}
        onOk={onUpload}
        onCancel={() => setUploadOpen(false)}
        confirmLoading={uploading}
        okText="Upload"
        width={620}
      >
        <Alert
          type="warning" style={{ marginBottom: 12 }} showIcon
          message={`Allowed file types: ${space.input_file_types.join(', ')}`}
        />
        <Form form={uploadForm} layout="vertical">
          <Form.Item label="File" required>
            <Upload
              accept={acceptHint}
              maxCount={1}
              beforeUpload={(f) => {
                setUploadFile({ uid: f.uid, name: f.name, originFileObj: f } as UploadFile);
                return false;
              }}
              onRemove={() => setUploadFile(null)}
              fileList={uploadFile ? [uploadFile] : []}
            >
              <Button icon={<UploadOutlined />}>Choose file</Button>
            </Upload>
          </Form.Item>
          <Form.Item name="expected_output" label="Expected output (JSON)" tooltip="What the model should produce for this sample. Used by the optimizer for scoring.">
            <Input.TextArea rows={6} placeholder='{ "title": "...", "amount": 0 }' />
          </Form.Item>
          <Form.Item name="document_context" label="Document context (optional)">
            <Input.TextArea rows={2} />
          </Form.Item>
        </Form>
      </Modal>

      <Modal
        title="Edit schema (JSON)"
        open={schemaOpen}
        onOk={onSaveSchema}
        onCancel={() => setSchemaOpen(false)}
        width={720}
      >
        <Input.TextArea
          rows={18}
          value={schemaText}
          onChange={(e) => setSchemaText(e.target.value)}
          style={{ fontFamily: 'monospace' }}
        />
        <Divider />
        <Typography.Text type="secondary">
          Save creates a new schema snapshot on this draft. Publishing freezes it.
        </Typography.Text>
      </Modal>
    </Space>
  );
}
