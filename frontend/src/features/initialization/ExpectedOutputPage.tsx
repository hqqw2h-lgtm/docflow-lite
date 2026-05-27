import { useEffect, useMemo, useState } from 'react';
import {
  App as AntdApp,
  Button,
  Card,
  Dropdown,
  Empty,
  Input,
  Segmented,
  Select,
  Space,
  Switch,
  Table,
  Tag,
  Typography
} from 'antd';
import type { ColumnsType } from 'antd/es/table';
import { DeleteOutlined, DownOutlined, PlusOutlined, SaveOutlined } from '@ant-design/icons';
import { useOutletContext } from 'react-router-dom';
import { workspacesApi } from '../../shared/api';
import { defaultExpectedOutputSchema, newOutputField, normalizeExpectedOutputSchema } from '../../defaults';
import type {
  ExpectedOutputSchema,
  OutputFieldType,
  OutputRootType,
  SchemaField
} from '../../shared/types';
import type { WorkspaceOutletContext } from '../../shared/layouts/WorkspaceShell';
import { addChild, countFields, removeField, updateField } from './schemaOps';

interface Row {
  key: string;
  path: number[];
  field: SchemaField;
  children?: Row[];
}

const TYPE_OPTIONS: { value: OutputFieldType; label: string }[] = [
  { value: 'string', label: 'String' },
  { value: 'number', label: 'Number' },
  { value: 'boolean', label: 'Boolean' },
  { value: 'date', label: 'Date' },
  { value: 'json', label: 'Nested JSON' },
  { value: 'jsonArray', label: 'JSON Array' }
];

function toRows(fields: SchemaField[], parentPath: number[] = []): Row[] {
  return fields.map((field, index) => {
    const path = [...parentPath, index];
    const isContainer = field.type === 'json' || field.type === 'jsonArray';
    return {
      key: path.join('.'),
      path,
      field,
      children: isContainer ? toRows(field.children ?? [], path) : undefined
    };
  });
}

export function ExpectedOutputPage() {
  const { workspace, setWorkspace } = useOutletContext<WorkspaceOutletContext>();
  const { message } = AntdApp.useApp();
  const [schema, setSchema] = useState<ExpectedOutputSchema>(defaultExpectedOutputSchema());
  const [dirty, setDirty] = useState(false);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    if (!workspace) return;
    setSchema(normalizeExpectedOutputSchema(workspace.schema_info));
    setDirty(false);
  }, [workspace?.id]); // eslint-disable-line react-hooks/exhaustive-deps

  const rows = useMemo(() => toRows(schema.children), [schema]);
  const fieldCount = useMemo(() => countFields(schema.children), [schema]);

  const applyChildren = (next: SchemaField[]) => {
    setSchema((prev) => ({ ...prev, children: next }));
    setDirty(true);
  };

  const onAddRoot = (type: OutputFieldType) => {
    applyChildren([...schema.children, newOutputField(type)]);
  };

  const onAddChild = (path: number[], type: OutputFieldType) => {
    applyChildren(addChild(schema.children, path, newOutputField(type)));
  };

  const onPatch = (path: number[], patch: Partial<SchemaField>) => {
    applyChildren(updateField(schema.children, path, patch));
  };

  const onRemove = (path: number[]) => {
    applyChildren(removeField(schema.children, path));
  };

  const save = async () => {
    if (!workspace) return;
    if (schema.children.some((field) => !field.fieldName.trim())) {
      message.error('All top-level fields need a name.');
      return;
    }
    setSaving(true);
    try {
      const updated = await workspacesApi.update(workspace.id, { schema_info: schema });
      setWorkspace(updated);
      setSchema(normalizeExpectedOutputSchema(updated.schema_info));
      setDirty(false);
      message.success('Expected output saved.');
    } catch (error) {
      message.error((error as Error).message);
    } finally {
      setSaving(false);
    }
  };

  const columns: ColumnsType<Row> = [
    {
      title: 'Field name',
      dataIndex: ['field', 'fieldName'],
      width: '34%',
      render: (_, row) => (
        <Input
          value={row.field.fieldName}
          placeholder="e.g. invoiceNumber"
          onChange={(event) => onPatch(row.path, { fieldName: event.target.value })}
        />
      )
    },
    {
      title: 'Type',
      dataIndex: ['field', 'type'],
      width: 160,
      render: (_, row) => (
        <Select
          value={row.field.type}
          options={TYPE_OPTIONS}
          style={{ width: '100%' }}
          onChange={(value) => onPatch(row.path, { type: value })}
        />
      )
    },
    {
      title: 'Required',
      dataIndex: ['field', 'isRequired'],
      width: 110,
      align: 'center',
      render: (_, row) => (
        <Switch
          size="small"
          checked={row.field.isRequired}
          onChange={(checked) => onPatch(row.path, { isRequired: checked })}
        />
      )
    },
    {
      title: 'Actions',
      width: 200,
      render: (_, row) => {
        const isContainer = row.field.type === 'json' || row.field.type === 'jsonArray';
        return (
          <Space>
            {isContainer && (
              <Dropdown
                menu={{
                  items: TYPE_OPTIONS.map((option) => ({ key: option.value, label: option.label })),
                  onClick: ({ key }) => onAddChild(row.path, key as OutputFieldType)
                }}
              >
                <Button size="small" icon={<PlusOutlined />}>
                  Add child <DownOutlined />
                </Button>
              </Dropdown>
            )}
            <Button
              size="small"
              danger
              type="text"
              icon={<DeleteOutlined />}
              onClick={() => onRemove(row.path)}
            />
          </Space>
        );
      }
    }
  ];

  return (
    <Card
      title={
        <Space align="center" size={12}>
          <Typography.Title level={4} style={{ margin: 0 }}>
            Expected Output
          </Typography.Title>
          <Tag color="blue">{fieldCount} fields</Tag>
        </Space>
      }
      extra={
        <Space>
          <Segmented
            value={schema.outputType}
            onChange={(value) =>
              setSchema((prev) => {
                setDirty(true);
                return { ...prev, outputType: value as OutputRootType };
              })
            }
            options={[
              { label: 'JSON object', value: 'json' },
              { label: 'JSON array', value: 'jsonArray' }
            ]}
          />
          <Dropdown
            menu={{
              items: TYPE_OPTIONS.map((option) => ({ key: option.value, label: option.label })),
              onClick: ({ key }) => onAddRoot(key as OutputFieldType)
            }}
          >
            <Button icon={<PlusOutlined />}>
              Add field <DownOutlined />
            </Button>
          </Dropdown>
          <Button type="primary" icon={<SaveOutlined />} loading={saving} disabled={!dirty} onClick={save}>
            Save
          </Button>
        </Space>
      }
    >
      <Typography.Paragraph type="secondary" style={{ marginTop: 0 }}>
        Define the JSON your model should return. Required fields will be validated. Nested JSON and
        JSON Array let you express hierarchical or table-like data.
      </Typography.Paragraph>
      <Table<Row>
        columns={columns}
        dataSource={rows}
        pagination={false}
        size="middle"
        rowKey="key"
        locale={{
          emptyText: <Empty description="No fields yet. Use ‘Add field’ to start." />
        }}
        expandable={{ defaultExpandAllRows: true, indentSize: 24 }}
      />
    </Card>
  );
}
