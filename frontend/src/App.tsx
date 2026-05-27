import { useEffect, useMemo, useState } from 'react';
import type { CSSProperties } from 'react';
import { api } from './api';
import { emptyIntegrationConfig, newOutputField, normalizeExpectedOutputSchema } from './defaults';
import { ProcessingTrace } from './features/documents/ProcessingTrace';
import { ProcessingSettingsPanel } from './features/processing/ProcessingSettingsPanel';
import type {
  ExtractionResult,
  IntegrationConfig,
  IntegrationWorkflow,
  ModelSettings,
  PromptProfile,
  ExpectedOutputSchema,
  SchemaField,
  SchemaInfo,
  Tenant,
  TrainingExampleSet,
  Workspace,
  WorkspaceBackgroundFile
} from './types';

type Tab = 'initialization' | 'examples' | 'prompts' | 'documents' | 'integration' | 'settings' | 'processing';

const jsonIndent = 2;
const legacySampleBatchId = 'legacy-draft';

export default function App() {
  const [tenants, setTenants] = useState<Tenant[]>([]);
  const [tenantId, setTenantId] = useState('');
  const [workspaces, setWorkspaces] = useState<Workspace[]>([]);
  const [selected, setSelected] = useState<Workspace | null>(null);
  const [query, setQuery] = useState('');
  const [activeFilter, setActiveFilter] = useState('');
  const [isCreating, setIsCreating] = useState(false);
  const [isTenantAdminOpen, setIsTenantAdminOpen] = useState(false);
  const [tab, setTab] = useState<Tab>('initialization');
  const [notice, setNotice] = useState('');

  const load = async () => {
    const params = new URLSearchParams();
    if (tenantId) params.set('tenant_id', tenantId);
    if (query) params.set('query', query);
    if (activeFilter) params.set('active', activeFilter);
    const suffix = params.size ? `?${params.toString()}` : '';
    const [tenantList, list] = await Promise.all([api.tenants(), api.workspaces(suffix)]);
    setTenants(tenantList);
    if (!tenantId && tenantList[0]) {
      setTenantId(tenantList[0].id);
    }
    setWorkspaces(list);
    if (selected) {
      setSelected(list.find((item) => item.id === selected.id) ?? null);
    }
  };

  useEffect(() => {
    void load().catch((error: Error) => setNotice(error.message));
  }, [tenantId, query, activeFilter]);

  const stats = useMemo(
    () => ({
      all: workspaces.length,
      active: workspaces.filter((item) => item.active_status).length,
      inactive: workspaces.filter((item) => !item.active_status).length
    }),
    [workspaces]
  );
  const selectedTenant = tenants.find((tenant) => tenant.id === tenantId) ?? tenants[0] ?? null;

  if (isTenantAdminOpen) {
    return (
      <ProductFrame
        activeSection="tenant-center"
        currentTenant={selectedTenant}
        tenants={tenants}
        tenantId={tenantId}
        notice={notice}
        onDismiss={() => setNotice('')}
        onTenantChange={setTenantId}
        onHome={() => setIsTenantAdminOpen(false)}
        onTenantCenter={() => setIsTenantAdminOpen(true)}
      >
        <TenantAdminPanel
          tenants={tenants}
          selectedTenantId={tenantId}
          onSelectTenant={setTenantId}
          onCreated={(tenant) => {
            setTenantId(tenant.id);
            void load();
          }}
          onNotice={setNotice}
        />
      </ProductFrame>
    );
  }

  if (selected) {
    return (
      <ProductFrame
        activeSection="workspace"
        currentTenant={selectedTenant}
        tenants={tenants}
        tenantId={tenantId}
        notice={notice}
        onDismiss={() => setNotice('')}
        onTenantChange={setTenantId}
        onHome={() => setSelected(null)}
        onTenantCenter={() => setIsTenantAdminOpen(true)}
        workspaceTab={tab}
        onWorkspaceTabChange={setTab}
      >
        <header className="detailHeader workspaceHeaderCompact">
          <div>
            <button className="linkButton" onClick={() => setSelected(null)}>
              ← Workspaces
            </button>
            <div className="workspaceTitleLine">
              <p className="eyebrow">Business Workspace</p>
              <h1>{selected.name}</h1>
            </div>
            <p>{selected.description || 'Business description is required before extraction or prompt analysis.'}</p>
          </div>
          <div className="statusStack">
            <span className={selected.active_status ? 'pill active' : 'pill'}>{selected.active_status ? 'Active' : 'Inactive'}</span>
            <span className={selected.initialization_status === 'active' ? 'pill active' : 'pill'}>
              Initialization {selected.initialization_status}
            </span>
          </div>
        </header>
        {tab === 'initialization' && (
          <BusinessContextPanel
            workspace={selected}
            onChange={(workspace) => {
              setSelected(workspace);
              void load();
            }}
            onNotice={setNotice}
          />
        )}
        {tab === 'initialization' && (
          <InitializationPanel
            workspace={selected}
            onChange={setSelected}
            onNotice={setNotice}
          />
        )}
        {tab === 'examples' && <TrainingExamplesPanel workspace={selected} onNotice={setNotice} refreshWorkspace={load} />}
        {tab === 'prompts' && (
          <PromptVersionsPanel
            workspace={selected}
            onChange={(workspace) => {
              setSelected(workspace);
              void load();
            }}
            onNotice={setNotice}
          />
        )}
        {tab === 'documents' && <ExtractedResultsPanel workspace={selected} onNotice={setNotice} />}
        {tab === 'integration' && <IntegrationPanel workspace={selected} onNotice={setNotice} />}
        {tab === 'settings' && <SettingsPanel onNotice={setNotice} />}
        {tab === 'processing' && <ProcessingSettingsPanel onNotice={setNotice} />}
      </ProductFrame>
    );
  }

  return (
    <ProductFrame
      activeSection="home"
      currentTenant={selectedTenant}
      tenants={tenants}
      tenantId={tenantId}
      notice={notice}
      onDismiss={() => setNotice('')}
      onTenantChange={setTenantId}
      onHome={() => undefined}
      onTenantCenter={() => setIsTenantAdminOpen(true)}
    >
      <header className="pageHeader">
        <div>
          <p className="eyebrow">Workspace Home</p>
          <h1>{selectedTenant?.name ?? 'Tenant'} Workspaces</h1>
          <p>Choose a business workspace, initialize samples, and activate extraction workflows.</p>
        </div>
        <button className="primary" onClick={() => setIsCreating(true)}>
          New Workspace
        </button>
      </header>
      <section className="stats">
        <Metric label="All" value={stats.all} />
        <Metric label="Active" value={stats.active} />
        <Metric label="Inactive" value={stats.inactive} />
      </section>
      <section className="toolbar">
        <input value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Search workspace" />
        <select value={activeFilter} onChange={(event) => setActiveFilter(event.target.value)}>
          <option value="">All status</option>
          <option value="true">Active</option>
          <option value="false">Inactive</option>
        </select>
      </section>
      <section className="grid">
        {workspaces.map((workspace) => (
          <button key={workspace.id} className="card workspaceCard" onClick={() => setSelected(workspace)}>
            <span className={workspace.active_status ? 'pill active' : 'pill'}>{workspace.active_status ? 'Active' : 'Inactive'}</span>
            <h2>{workspace.name}</h2>
            <p>{workspace.description || 'Business description missing'}</p>
            <div className="cardMeta">
              <span>Business context</span>
              <span>{workspace.extracted ? 'Has extraction' : 'No extraction'}</span>
            </div>
          </button>
        ))}
      </section>
      {isCreating && (
        <CreateWorkspaceDialog
          tenantId={tenantId || tenants[0]?.id || 'local-tenant'}
          onClose={() => setIsCreating(false)}
          onCreated={(workspace) => {
            setIsCreating(false);
            setSelected(workspace);
            void load();
          }}
          onNotice={setNotice}
        />
      )}
    </ProductFrame>
  );
}

function ProductFrame({
  children,
  activeSection,
  currentTenant,
  tenants,
  tenantId,
  notice,
  onDismiss,
  onTenantChange,
  onHome,
  onTenantCenter,
  workspaceTab,
  onWorkspaceTabChange
}: {
  children: React.ReactNode;
  activeSection: 'home' | 'tenant-center' | 'workspace';
  currentTenant: Tenant | null;
  tenants: Tenant[];
  tenantId: string;
  notice: string;
  onDismiss: () => void;
  onTenantChange: (tenantId: string) => void;
  onHome: () => void;
  onTenantCenter: () => void;
  workspaceTab?: Tab;
  onWorkspaceTabChange?: (tab: Tab) => void;
}) {
  return (
    <div className="productShell">
      <aside className="sideNav">
        <div className="brandBlock">
          <div className="brandMark">D</div>
          <div>
            <strong>DocFlow Lite</strong>
            <span>Document AI Platform</span>
          </div>
        </div>
        <div className="tenantSwitcher">
          <label>
            Tenant
            <select value={tenantId} onChange={(event) => onTenantChange(event.target.value)}>
              {tenants.map((tenant) => (
                <option key={tenant.id} value={tenant.id}>
                  {tenant.name}
                </option>
              ))}
            </select>
          </label>
        </div>
        <nav className="sideMenu" aria-label="Primary">
          <button className={activeSection === 'home' || activeSection === 'workspace' ? 'sideItem active' : 'sideItem'} onClick={onHome}>
            <span>01</span>
            Workspace Home
          </button>
          {activeSection === 'workspace' && workspaceTab && onWorkspaceTabChange && (
            <WorkspaceSubMenu activeTab={workspaceTab} onChange={onWorkspaceTabChange} />
          )}
          <button className={activeSection === 'tenant-center' ? 'sideItem active' : 'sideItem'} onClick={onTenantCenter}>
            <span>02</span>
            Tenant Center
          </button>
        </nav>
        <div className="sideHint">
          <strong>Current role</strong>
          <span>Tenant Owner</span>
        </div>
      </aside>
      <section className="mainArea">
        <header className="topBar">
          <div>
            <p className="eyebrow">Good morning</p>
            <h2>{currentTenant?.name ?? 'No tenant selected'}</h2>
          </div>
          <div className="topMeta">
            <span>{activeSection === 'tenant-center' ? 'Admin' : 'Workspace'}</span>
            <span>{new Date().toLocaleDateString()}</span>
          </div>
        </header>
        <main className="contentArea">
          {notice && (
            <div className="notice" role="status">
              <span>{notice}</span>
              <button onClick={onDismiss}>Dismiss</button>
            </div>
          )}
          {children}
        </main>
      </section>
    </div>
  );
}

function Metric({ label, value }: { label: string; value: number }) {
  return (
    <div className="metric">
      <span>{label}</span>
      <strong>{value}</strong>
    </div>
  );
}

function BusinessContextPanel({
  workspace,
  onChange,
  onNotice
}: {
  workspace: Workspace;
  onChange: (workspace: Workspace) => void;
  onNotice: (message: string) => void;
}) {
  const [description, setDescription] = useState(workspace.description);
  const [files, setFiles] = useState<WorkspaceBackgroundFile[]>([]);
  const [isUploading, setIsUploading] = useState(false);

  useEffect(() => {
    setDescription(workspace.description);
  }, [workspace.id, workspace.description]);

  useEffect(() => {
    void api.backgroundFiles(workspace.id)
      .then(setFiles)
      .catch((error: Error) => onNotice(error.message));
  }, [workspace.id, onNotice]);

  const save = async () => {
    const trimmed = description.trim();
    if (!trimmed) {
      onNotice('Business description is required before extraction or prompt analysis.');
      return;
    }
    try {
      const updated = await api.updateWorkspace(workspace.id, { description: trimmed });
      onChange(updated);
      onNotice('Business description saved.');
    } catch (error) {
      onNotice((error as Error).message);
    }
  };

  const uploadBackground = async (file: File | null) => {
    if (!file) return;
    setIsUploading(true);
    try {
      const result = await api.uploadBackgroundFile(workspace.id, file);
      setDescription(result.suggested_description);
      setFiles((current) => [result.file, ...current]);
      onChange(result.workspace);
      onNotice('Business context summarized from uploaded background file.');
    } catch (error) {
      onNotice((error as Error).message);
    } finally {
      setIsUploading(false);
    }
  };

  return (
    <section className={workspace.description.trim() ? 'businessContextPanel' : 'businessContextPanel required'}>
      <div>
        <p className="eyebrow">Business Context</p>
        <h2>Workspace description</h2>
        <p>Upload PDF, Excel, text, or screenshots. AI summarizes the business background and saves it as model context.</p>
      </div>
      <div className="businessContextEditor">
        <label>
          Business Description
          <textarea
            value={description}
            onChange={(event) => setDescription(event.target.value)}
            placeholder="Upload business background files to generate this automatically, or edit the generated description."
            required
          />
        </label>
        <div className="backgroundFileList">
          {files.map((item) => (
            <span key={item.id}>{item.file_name}</span>
          ))}
        </div>
      </div>
      <div className="contextActions">
        <label className="fileButton">
          {isUploading ? 'Summarizing...' : 'Upload Background'}
          <input
            type="file"
            accept=".pdf,.xlsx,.xlsm,.txt,.md,.csv,.json,.png,.jpg,.jpeg,.webp"
            onChange={(event) => void uploadBackground(event.target.files?.[0] ?? null)}
            disabled={isUploading}
          />
        </label>
        <button className="primary" onClick={save} disabled={!description.trim()}>
          Save Context
        </button>
      </div>
    </section>
  );
}

function TenantAdminPanel({
  tenants,
  selectedTenantId,
  onSelectTenant,
  onCreated,
  onNotice
}: {
  tenants: Tenant[];
  selectedTenantId: string;
  onSelectTenant: (tenantId: string) => void;
  onCreated: (tenant: Tenant) => void;
  onNotice: (message: string) => void;
}) {
  const [name, setName] = useState('');
  const [description, setDescription] = useState('');

  const createTenant = async () => {
    try {
      const tenant = await api.createTenant({ name, description });
      setName('');
      setDescription('');
      onCreated(tenant);
      onNotice('Tenant created.');
    } catch (error) {
      onNotice((error as Error).message);
    }
  };

  return (
    <section className="adminLayout">
      <header className="adminHero">
        <p className="eyebrow">Admin area</p>
        <h1>Tenant Management</h1>
        <p>Tenants are top-level containers for workspaces and model defaults. In a production version, this page should be protected by administrator permission.</p>
      </header>
      <div className="adminGrid">
        <section className="panel">
          <div className="panelHeader">
            <div>
              <h2>Tenants</h2>
              <p>Select the tenant context used by Workspace Home.</p>
            </div>
          </div>
          <div className="tenantList">
            {tenants.map((tenant) => (
              <button
                key={tenant.id}
                className={tenant.id === selectedTenantId ? 'tenantItem active' : 'tenantItem'}
                onClick={() => onSelectTenant(tenant.id)}
              >
                <strong>{tenant.name}</strong>
                <span>{tenant.description || 'No description'}</span>
              </button>
            ))}
          </div>
        </section>
        <section className="panel">
          <div className="panelHeader">
            <div>
              <h2>Create Tenant</h2>
              <p>This belongs in administrator flow, not the normal workspace operation flow.</p>
            </div>
          </div>
          <label>
            Tenant Name
            <input value={name} onChange={(event) => setName(event.target.value)} />
          </label>
          <label>
            Description
            <textarea value={description} onChange={(event) => setDescription(event.target.value)} />
          </label>
          <button className="primary" onClick={createTenant} disabled={!name.trim()}>
            Create Tenant
          </button>
        </section>
      </div>
    </section>
  );
}

function CreateWorkspaceDialog({
  tenantId,
  onClose,
  onCreated,
  onNotice
}: {
  tenantId: string;
  onClose: () => void;
  onCreated: (workspace: Workspace) => void;
  onNotice: (message: string) => void;
}) {
  const [name, setName] = useState('');
  const [description, setDescription] = useState('');

  const submit = async () => {
    const trimmedName = name.trim();
    const trimmedDescription = description.trim();
    if (!trimmedName) {
      onNotice('Workspace name is required.');
      return;
    }
    try {
      const workspace = await api.createWorkspace({
        tenant_id: tenantId,
        name: trimmedName,
        description: trimmedDescription
      });
      onCreated(workspace);
    } catch (error) {
      onNotice((error as Error).message);
    }
  };

  return (
    <div className="dialogBackdrop" role="presentation">
      <section className="dialog" role="dialog" aria-modal="true" aria-label="Create workspace">
        <h2>Create Workspace</h2>
        <label>
          Workspace Name
          <input value={name} onChange={(event) => setName(event.target.value)} autoFocus />
        </label>
        <label>
          Business Description
          <textarea
            value={description}
            onChange={(event) => setDescription(event.target.value)}
            placeholder="Optional. You can leave this empty and upload PDF, Excel, text, or screenshots in the workspace to let AI summarize it."
          />
        </label>
        <footer className="actions">
          <button onClick={onClose}>Cancel</button>
          <button className="primary" onClick={submit} disabled={!name.trim()}>
            Create
          </button>
        </footer>
      </section>
    </div>
  );
}

function InitializationPanel({
  workspace,
  onChange,
  onNotice
}: {
  workspace: Workspace;
  onChange: (workspace: Workspace) => void;
  onNotice: (message: string) => void;
}) {
  const [schema, setSchema] = useState<ExpectedOutputSchema>(() => normalizeExpectedOutputSchema(workspace.schema_info));

  useEffect(() => setSchema(normalizeExpectedOutputSchema(workspace.schema_info)), [workspace.id, workspace.schema_info]);

  const save = async () => {
    try {
      const updated = await api.updateWorkspace(workspace.id, { schema_info: schema });
      onChange(updated);
      onNotice('Schema saved.');
    } catch (error) {
      onNotice((error as Error).message);
    }
  };

  const addRootField = (type: SchemaField['type']) => setSchema({ ...schema, children: [...schema.children, newOutputField(type)] });

  return (
    <section className="panel">
      <div className="panelHeader">
        <div>
          <h2>Expected Output</h2>
          <p>Add the fields the AI must return. After saving, open Samples in the left menu and upload real files for review.</p>
        </div>
      </div>
      <div className="schemaTable">
        <div className="schemaTableHeader" aria-hidden="true">
          <span>#</span>
          <span>Field Name</span>
          <span>Type</span>
          <span>Required</span>
          <span>Actions</span>
        </div>
        <div className="schemaRows">
          {schema.children.map((field, fieldIndex) => (
            <OutputFieldEditor
              key={fieldIndex}
              field={field}
              path={[fieldIndex]}
              depth={0}
              onUpdate={(path, patch) => setSchema({ ...schema, children: updateOutputField(schema.children, path, patch) })}
              onRemove={(path) => setSchema({ ...schema, children: removeOutputField(schema.children, path) })}
              onAddChild={(path, type) => setSchema({ ...schema, children: addOutputChild(schema.children, path, newOutputField(type)) })}
              onNotice={onNotice}
            />
          ))}
        </div>
        {schema.children.length === 0 && (
          <div className="emptySchemaState">
            <strong>No default fields</strong>
            <p>Start with fields from your own business output. Nothing is prefilled or hardcoded.</p>
          </div>
        )}
        <div className="schemaAddRow">
          <div className="actions">
            <button className="addFieldButton" onClick={() => addRootField('string')}>+ Add Field</button>
            <button onClick={() => addRootField('json')}>+ Nested JSON</button>
            <button onClick={() => addRootField('jsonArray')}>+ JSON Array</button>
          </div>
        </div>
      </div>
      <div className="schemaActionsBar">
        <span className="hintText">Save after editing fields, then add training examples in the workspace menu.</span>
        <div className="actions">
          <button className="primary" onClick={save}>
            Save Output
          </button>
        </div>
      </div>
      <div className="nextStepCard">
        <strong>Next step</strong>
        <p>Open Samples in the left menu, upload example files, check each generated JSON row, then publish a prompt version when the examples look correct.</p>
      </div>
    </section>
  );
}

function OutputFieldEditor({
  field,
  path,
  depth,
  onUpdate,
  onRemove,
  onAddChild,
  onNotice
}: {
  field: SchemaField;
  path: number[];
  depth: number;
  onUpdate: (path: number[], patch: Partial<SchemaField>) => void;
  onRemove: (path: number[]) => void;
  onAddChild: (path: number[], type: SchemaField['type']) => void;
  onNotice: (message: string) => void;
}) {
  const isComplex = field.type === 'json' || field.type === 'jsonArray';
  const rowNumber = String((path[path.length - 1] ?? 0) + 1).padStart(2, '0');

  const updateType = (type: SchemaField['type']) => {
    const supportsTextValidation = type === 'string' || type === 'date';
    onUpdate(path, {
      type,
      regexPattern: supportsTextValidation ? field.regexPattern : '',
      constraints: compatibleConstraints(field.constraints ?? {}, type),
      children: type === 'json' || type === 'jsonArray' ? field.children ?? [] : undefined
    });
  };

  return (
    <div className="schemaGroup" style={{ paddingLeft: `${depth * 24}px` } as CSSProperties}>
      <div className="schemaFieldRow">
        <div className="rowIndex">
          <span className="dragHandle">=</span>
          <span>{rowNumber}</span>
        </div>
        <input
          value={field.fieldName}
          onChange={(event) => onUpdate(path, { fieldName: event.target.value })}
          placeholder="Enter field name (required)"
          aria-label="Field name"
          title="The JSON key in the final output, for example invoiceNumber, amount, supplierName."
        />
        <select
          value={field.type}
          onChange={(event) => updateType(event.target.value as SchemaField['type'])}
          aria-label="Field type"
          title="The value type the model must return for this field. Use JSON or JSON Array for nested structures."
        >
          <option value="string">String</option>
          <option value="number">Number</option>
          <option value="boolean">Boolean</option>
          <option value="date">Date</option>
          <option value="json">JSON</option>
          <option value="jsonArray">JSON Array</option>
        </select>
        <label className="requiredSwitch" title="When enabled, extraction is invalid if this field is missing or empty.">
          <input type="checkbox" checked={field.isRequired} onChange={(event) => onUpdate(path, { isRequired: event.target.checked })} />
          <span>Required</span>
        </label>
        <div className="schemaRowActions">
          <button onClick={() => onRemove(path)}>Remove</button>
        </div>
      </div>
      <details className="fieldAdvanced">
        <summary>Optional validation and AI helper</summary>
        <RuleSuggestionPanel
          field={field}
          onApply={(patch) => onUpdate(path, patch)}
          onNotice={onNotice}
        />
        <ConstraintEditor
          fieldType={field.type}
          regexPattern={field.regexPattern ?? ''}
          constraints={field.constraints ?? {}}
          ignored={field.ignored ?? false}
          onRegexChange={(regexPattern) => onUpdate(path, { regexPattern })}
          onIgnoredChange={(ignored) => onUpdate(path, { ignored })}
          onChange={(constraints) => onUpdate(path, { constraints })}
        />
      </details>
      {isComplex && (
        <div className="nestedFields">
          <div className="nestedFieldHeader">
            <span>{field.type === 'jsonArray' ? 'Array item fields' : 'Nested JSON fields'}</span>
            <div className="actions">
              <button onClick={() => onAddChild(path, 'string')}>+ Field</button>
              <button onClick={() => onAddChild(path, 'json')}>+ JSON</button>
              <button onClick={() => onAddChild(path, 'jsonArray')}>+ JSON Array</button>
            </div>
          </div>
          {(field.children ?? []).map((child, childIndex) => (
            <OutputFieldEditor
              key={childIndex}
              field={child}
              path={[...path, childIndex]}
              depth={depth + 1}
              onUpdate={onUpdate}
              onRemove={onRemove}
              onAddChild={onAddChild}
              onNotice={onNotice}
            />
          ))}
        </div>
      )}
    </div>
  );
}

function RuleSuggestionPanel({
  field,
  onApply,
  onNotice
}: {
  field: SchemaField;
  onApply: (patch: Partial<SchemaField>) => void;
  onNotice: (message: string) => void;
}) {
  const [description, setDescription] = useState('');
  const [isGenerating, setIsGenerating] = useState(false);

  const generate = async () => {
    const trimmed = description.trim();
    if (!trimmed) {
      onNotice('Describe the rule first, for example: material number is exactly 10 uppercase letters or digits.');
      return;
    }
    setIsGenerating(true);
    try {
      const suggestion = await api.suggestFieldRule({ description: trimmed, field_type: field.type });
      const mergedConstraints = { ...(field.constraints ?? {}), ...suggestion.constraints };
      onApply({
        regexPattern: field.type === 'string' || field.type === 'date' ? suggestion.regexPattern || field.regexPattern : '',
        constraints: compatibleConstraints(mergedConstraints, field.type)
      });
      onNotice(suggestion.explanation || 'Validation rule generated.');
    } catch (error) {
      onNotice((error as Error).message);
    } finally {
      setIsGenerating(false);
    }
  };

  return (
    <div className="ruleSuggestion">
      <label title="Describe the business rule in normal language. The local model will suggest regex and hard constraints.">
        Describe validation rule
        <textarea
          value={description}
          onChange={(event) => setDescription(event.target.value)}
          placeholder="Example: material number must be exactly 10 uppercase letters or digits."
        />
      </label>
      <button onClick={generate} disabled={isGenerating}>
        {isGenerating ? 'Generating...' : 'Generate rule'}
      </button>
    </div>
  );
}

function ConstraintEditor({
  fieldType,
  regexPattern,
  constraints,
  ignored,
  onRegexChange,
  onIgnoredChange,
  onChange
}: {
  fieldType: SchemaField['type'];
  regexPattern: string;
  constraints: Record<string, unknown>;
  ignored: boolean;
  onRegexChange: (regexPattern: string) => void;
  onIgnoredChange: (ignored: boolean) => void;
  onChange: (constraints: Record<string, unknown>) => void;
}) {
  const supportsNumberRules = fieldType === 'number';
  const supportsTextRules = fieldType === 'string' || fieldType === 'date';
  const updateString = (key: string, value: string) => {
    const next = { ...constraints };
    if (value.trim()) {
      next[key] = value.trim();
    } else {
      delete next[key];
    }
    onChange(next);
  };
  const updateNumber = (key: string, value: string) => {
    const next = { ...constraints };
    if (value === '') {
      delete next[key];
    } else {
      const numericValue = Number(value);
      if (Number.isFinite(numericValue)) {
        next[key] = numericValue;
      }
    }
    onChange(next);
  };

  return (
    <div className="constraintGrid">
      {supportsTextRules && (
        <label title="A regex the final field value should match. Leave empty if you do not need a regex.">
          Regex Pattern
          <input value={regexPattern} placeholder="e.g. ^[A-Z0-9]{10}$" onChange={(event) => onRegexChange(event.target.value)} />
        </label>
      )}
      {supportsNumberRules && (
        <>
          <label title="For number fields: reject values smaller than this value.">
            Minimum value
            <input type="number" value={constraintText(constraints.min)} onChange={(event) => updateNumber('min', event.target.value)} />
          </label>
          <label title="For number fields: reject values greater than this value.">
            Maximum value
            <input type="number" value={constraintText(constraints.max)} onChange={(event) => updateNumber('max', event.target.value)} />
          </label>
        </>
      )}
      {supportsTextRules && (
        <>
          <label title="For string/date fields: reject values shorter than this character count.">
            Minimum length
            <input type="number" min="0" step="1" value={constraintText(constraints.minLength)} onChange={(event) => updateNumber('minLength', event.target.value)} />
          </label>
          <label title="For string/date fields: reject values longer than this character count.">
            Maximum length
            <input type="number" min="0" step="1" value={constraintText(constraints.maxLength)} onChange={(event) => updateNumber('maxLength', event.target.value)} />
          </label>
          <label title="For string/date fields: require exactly this character count. Useful for material numbers or IDs.">
            Exact length
            <input type="number" min="0" step="1" value={constraintText(constraints.exactLength)} onChange={(event) => updateNumber('exactLength', event.target.value)} />
          </label>
          <label title="Hard validation regex. This is checked after model output and can trigger automatic repair.">
            Hard pattern
            <input value={constraintText(constraints.pattern)} placeholder="Hard validation regex" onChange={(event) => updateString('pattern', event.target.value)} />
          </label>
        </>
      )}
      <label className="checkbox" title="Use this when the field exists in the schema draft but should not be extracted or validated.">
        <input type="checkbox" checked={ignored} onChange={(event) => onIgnoredChange(event.target.checked)} />
        Ignore this field
      </label>
      {!supportsNumberRules && !supportsTextRules && <p className="hintText">This field type only supports Required and Ignore. Configure child fields for JSON structures.</p>}
    </div>
  );
}

function PromptVersionLab({
  workspace,
  profiles,
  onActivated,
  onNotice
}: {
  workspace: Workspace;
  profiles: PromptProfile[];
  onActivated: (workspace: Workspace) => void;
  onNotice: (message: string) => void;
}) {
  const sortedProfiles = [...profiles].sort((a, b) => b.version - a.version);
  const activeProfile = sortedProfiles.find((profile) => profile.id === workspace.active_prompt_profile_id || profile.status === 'active') ?? sortedProfiles[0] ?? null;
  const [leftId, setLeftId] = useState('');
  const [rightId, setRightId] = useState('');

  useEffect(() => {
    setLeftId(activeProfile?.id ?? '');
    setRightId(sortedProfiles.find((profile) => profile.id !== activeProfile?.id)?.id ?? activeProfile?.id ?? '');
  }, [workspace.active_prompt_profile_id, profiles.length]);

  const left = sortedProfiles.find((profile) => profile.id === leftId) ?? activeProfile;
  const right = sortedProfiles.find((profile) => profile.id === rightId) ?? sortedProfiles.find((profile) => profile.id !== left?.id) ?? left;

  const activate = async (profile: PromptProfile | null) => {
    if (!profile) return;
    try {
      const updated = await api.activatePromptProfile(workspace.id, profile.id);
      onActivated(updated);
      onNotice(`Prompt profile v${profile.version} activated.`);
    } catch (error) {
      onNotice((error as Error).message);
    }
  };

  if (profiles.length === 0) {
    return (
      <section className="card promptVersionLab">
        <h3>Prompt Versions</h3>
        <p>No prompt version generated yet. Open Samples, confirm rows, then generate a prompt version.</p>
      </section>
    );
  }

  return (
    <section className="card promptVersionLab">
      <div className="panelHeader">
        <div>
          <h3>Version Comparison</h3>
          <p>Select two versions to compare prompts, examples, fields, and model settings before switching production extraction.</p>
        </div>
        <button className="primary" onClick={() => activate(left)}>
          Use / Activate v{left?.version ?? '-'}
        </button>
      </div>
      <div className="versionSelectors">
        <label>
          Candidate version
          <select value={left?.id ?? ''} onChange={(event) => setLeftId(event.target.value)}>
            {sortedProfiles.map((profile) => (
              <option key={profile.id} value={profile.id}>
                v{profile.version} · {profile.status}
              </option>
            ))}
          </select>
        </label>
        <label>
          Compare with
          <select value={right?.id ?? ''} onChange={(event) => setRightId(event.target.value)}>
            {sortedProfiles.map((profile) => (
              <option key={profile.id} value={profile.id}>
                v{profile.version} · {profile.status}
              </option>
            ))}
          </select>
        </label>
      </div>
      <div className="versionCompare">
        <PromptVersionCard profile={left} title="Candidate" />
        <PromptVersionCard profile={right} title="Baseline" />
      </div>
    </section>
  );
}

function PromptVersionCard({ profile, title }: { profile: PromptProfile | null; title: string }) {
  if (!profile) {
    return <div className="versionCard">No version selected.</div>;
  }
  const fieldCount = countOutputFields(profile.output_contract);
  return (
    <div className={profile.status === 'active' ? 'versionCard active' : 'versionCard'}>
      <div className="versionHeader">
        <span>{title}</span>
        <strong>v{profile.version}</strong>
        <em>{profile.status}</em>
      </div>
      <dl className="versionMetrics">
        <div>
          <dt>Fields</dt>
          <dd>{fieldCount}</dd>
        </div>
        <div>
          <dt>Examples</dt>
          <dd>{profile.few_shot_examples.length}</dd>
        </div>
        <div>
          <dt>Model</dt>
          <dd>{profile.model_name}</dd>
        </div>
      </dl>
      <h4>Extraction Instruction</h4>
      <p>{profile.extraction_instruction}</p>
      <h4>System Prompt</h4>
      <p>{profile.system_prompt}</p>
    </div>
  );
}

function WorkspaceSubMenu({ activeTab, onChange }: { activeTab: Tab; onChange: (tab: Tab) => void }) {
  const items: Array<{ tab: Tab; title: string; description: string }> = [
    { tab: 'initialization', title: 'Expected Output', description: 'Output structure and validation' },
    { tab: 'examples', title: 'Samples', description: 'Upload, review, and confirm' },
    { tab: 'prompts', title: 'Prompt Versions', description: 'Publish and activate' },
    { tab: 'documents', title: 'Extracted Results', description: 'Runs and traces' },
    { tab: 'integration', title: 'Integration', description: 'Workflow delivery' },
    { tab: 'settings', title: 'Model', description: 'Provider and model' },
    { tab: 'processing', title: 'Processing', description: 'Markdown and context budget' }
  ];

  return (
    <nav className="workspaceSubMenu" aria-label="Workspace menu">
      {items.map((item) => (
        <button
          key={item.tab}
          className={activeTab === item.tab ? 'subMenuItem active' : 'subMenuItem'}
          onClick={() => onChange(item.tab)}
        >
          <strong>{item.title}</strong>
          <small>{item.description}</small>
        </button>
      ))}
    </nav>
  );
}

function PromptVersionsPanel({
  workspace,
  onChange,
  onNotice
}: {
  workspace: Workspace;
  onChange: (workspace: Workspace) => void;
  onNotice: (message: string) => void;
}) {
  const [profiles, setProfiles] = useState<PromptProfile[]>([]);

  const load = async () => {
    setProfiles(await api.promptProfiles(workspace.id));
  };

  useEffect(() => {
    void load().catch((error: Error) => onNotice(error.message));
  }, [workspace.id]);

  const activeProfile = profiles.find((profile) => profile.id === workspace.active_prompt_profile_id || profile.status === 'active') ?? null;

  return (
    <section className="panel promptVersionsPage">
      <div className="panelHeader">
        <div>
          <h2>Prompt Versions</h2>
          <p>Business users use a version by activating it here. The active version is used by extraction runs and API calls for this workspace.</p>
        </div>
        <span className={activeProfile ? 'pill active' : 'pill'}>
          {activeProfile ? `Using v${activeProfile.version}` : 'No active version'}
        </span>
      </div>
      <div className="versionUsageCard">
        <div>
          <p className="eyebrow">How a version is used</p>
          <h3>Activate the prompt version you want production extraction to use</h3>
          <p>
            Generating from confirmed sample rows creates a prompt version. Activating it makes it the current extraction strategy for this workspace.
          </p>
        </div>
        <dl className="versionMetrics">
          <div>
            <dt>Versions</dt>
            <dd>{profiles.length}</dd>
          </div>
          <div>
            <dt>Active</dt>
            <dd>{activeProfile ? `v${activeProfile.version}` : '-'}</dd>
          </div>
          <div>
            <dt>Model</dt>
            <dd>{activeProfile?.model_name ?? '-'}</dd>
          </div>
        </dl>
      </div>
      <PromptVersionLab
        workspace={workspace}
        profiles={profiles}
        onActivated={(updated) => {
          onChange(updated);
          void load().catch((error: Error) => onNotice(error.message));
        }}
        onNotice={onNotice}
      />
    </section>
  );
}
function TrainingExamplesPanel({
  workspace,
  onNotice,
  refreshWorkspace
}: {
  workspace: Workspace;
  onNotice: (message: string) => void;
  refreshWorkspace: () => Promise<void>;
}) {
  const [results, setResults] = useState<ExtractionResult[]>([]);
  const [selected, setSelected] = useState<ExtractionResult | null>(null);
  const [jsonText, setJsonText] = useState('');
  const [documentContext, setDocumentContext] = useState('');
  const [exampleSets, setExampleSets] = useState<TrainingExampleSet[]>([]);
  const [selectedSetId, setSelectedSetId] = useState('');

  const load = async () => {
    const [list, sets] = await Promise.all([api.results(workspace.id), api.exampleSets(workspace.id)]);
    setResults(list);
    setExampleSets(sets);
    setSelectedSetId((current) => current || sets.find((item) => item.status === 'draft')?.id || sets[0]?.id || '');
    setSelected((current) => (current ? list.find((item) => item.id === current.id) ?? list[0] ?? null : list[0] ?? null));
  };

  useEffect(() => {
    void load().catch((error: Error) => onNotice(error.message));
  }, [workspace.id]);

  useEffect(() => {
    if (selected) {
      const data = hasPayload(selected.corrected_data) ? selected.corrected_data : selected.extracted_data;
      setJsonText(JSON.stringify(data, null, jsonIndent));
    }
  }, [selected]);

  const upload = async (file: File | null) => {
    if (!file) return;
    try {
      await api.extract(workspace.id, file, documentContext);
      await load();
      await refreshWorkspace();
      onNotice('File extracted and ready for review.');
    } catch (error) {
      onNotice((error as Error).message);
    }
  };
  const selectedSet = exampleSets.find((item) => item.id === selectedSetId) ?? exampleSets[0] ?? null;
  const draftSet = exampleSets.find((item) => item.status === 'draft') ?? null;
  const resultByExampleId = new Map(results.map((result) => [result.id, result]));
  const canEditSelectedSet = selectedSet?.status === 'draft';
  const canManageSelectedSet = Boolean(selectedSet && selectedSet.id !== legacySampleBatchId);
  const selectedExamples = selectedSet?.examples ?? [];

  useEffect(() => {
    if (!selectedSet) {
      setSelected(null);
      return;
    }

    const selectedResultIds = new Set(selectedSet.examples.map((example) => example.extraction_result_id));
    if (selected && selectedResultIds.has(selected.id)) return;

    const nextSelected = selectedSet.examples.map((example) => resultByExampleId.get(example.extraction_result_id)).find((result): result is ExtractionResult => Boolean(result)) ?? null;
    setSelected(nextSelected);
  }, [selectedSetId, exampleSets, results]);

  const freezeSelectedSet = async () => {
    if (!selectedSet) return;
    try {
      const result = await api.freezeExampleSet(workspace.id, selectedSet.id);
      await load();
      await refreshWorkspace();
      onNotice(`Sample batch v${selectedSet.version} published. Prompt version v${result.prompt_profile_version} generated from ${result.sample_count} sample(s).`);
    } catch (error) {
      onNotice((error as Error).message);
    }
  };

  const cloneSelectedSet = async () => {
    if (!selectedSet) return;
    try {
      const cloned = await api.cloneExampleSet(workspace.id, selectedSet.id);
      await load();
      setSelectedSetId(cloned.id);
      onNotice(`Sample batch v${selectedSet.version} copied to editable draft v${cloned.version}.`);
    } catch (error) {
      onNotice((error as Error).message);
    }
  };

  const removeExample = async (exampleId: string) => {
    if (!selectedSet) return;
    try {
      await api.removeExampleFromSet(workspace.id, selectedSet.id, exampleId);
      await load();
      onNotice('Sample removed from this draft batch.');
    } catch (error) {
      onNotice((error as Error).message);
    }
  };

  const confirm = async () => {
    if (!selected) return;
    try {
      const parsed = JSON.parse(jsonText) as Record<string, unknown>;
      await api.updateResult(selected.id, { corrected_data: parsed, status: 'completed' });
      await load();
      onNotice('Correction confirmed. This row can be used when you generate a prompt version.');
    } catch (error) {
      onNotice((error as Error).message);
    }
  };

  return (
    <section className="panel samplesPanel">
      <div className="panelHeader">
        <div>
          <h2>Samples</h2>
          <p>Every uploaded file is one table row. Review the JSON row, confirm it, then generate a prompt version from confirmed rows.</p>
        </div>
      </div>
      <div className="samplesToolbar">
        <label className="compactControl">
          Sample batch
          <select value={selectedSet?.id ?? ''} disabled={exampleSets.length === 0} onChange={(event) => setSelectedSetId(event.target.value)}>
            {exampleSets.map((item) => (
              <option key={item.id} value={item.id}>
                {item.status === 'draft' ? 'Draft' : 'Published'} batch v{item.version}
              </option>
            ))}
          </select>
        </label>
        <label className="upload sampleUpload">
          Upload sample file
          <input type="file" disabled={!draftSet || !canEditSelectedSet} onChange={(event) => void upload(event.target.files?.[0] ?? null)} />
        </label>
        <button className="primary" disabled={!selectedSet || !canEditSelectedSet || !canManageSelectedSet} onClick={freezeSelectedSet}>
          Generate Prompt Version
        </button>
        <button disabled={!selectedSet || !canManageSelectedSet} onClick={cloneSelectedSet}>
          Copy as New Draft
        </button>
      </div>
      {selectedSet?.status === 'frozen' && <p className="hintText">Published sample batches are read-only. Copy this batch to create an editable draft.</p>}
      <div className="sampleTableWrap">
        <table className="sampleTable">
          <thead>
            <tr>
              <th>#</th>
              <th>File</th>
              <th>Status</th>
              <th>Batch</th>
              <th>Updated</th>
              <th>Actions</th>
            </tr>
          </thead>
          <tbody>
            {selectedExamples.length === 0 ? (
              <tr>
                <td colSpan={6} className="emptyTableCell">
                  No samples yet. Upload a file to create the first row.
                </td>
              </tr>
            ) : (
              selectedExamples.map((example, index) => {
                const result = resultByExampleId.get(example.extraction_result_id);
                const isActive = selected?.id === result?.id;
                return (
                  <tr key={example.id} className={isActive ? 'active' : undefined}>
                    <td>{index + 1}</td>
                    <td>
                      <strong>{result?.file_name ?? example.id}</strong>
                      <small>{result?.model ?? 'No extraction result'}</small>
                    </td>
                    <td>
                      <span className={example.status === 'accepted' ? 'pill active' : 'pill'}>{example.status.replaceAll('_', ' ')}</span>
                    </td>
                    <td>{selectedSet ? `${selectedSet.status === 'draft' ? 'Draft' : 'Published'} v${selectedSet.version}` : '-'}</td>
                    <td>{new Date(example.updated_at).toLocaleString()}</td>
                    <td>
                      <div className="tableActions">
                        <button disabled={!result} onClick={() => result && setSelected(result)}>
                          Review JSON
                        </button>
                        {canEditSelectedSet && canManageSelectedSet && (
                          <button onClick={() => removeExample(example.id)} title="Remove this sample from the current draft batch. The original extraction result is kept.">
                            Remove
                          </button>
                        )}
                      </div>
                    </td>
                  </tr>
                );
              })
            )}
          </tbody>
        </table>
      </div>
      <details className="sampleContextPanel">
        <summary>Optional context for next upload</summary>
        <textarea
          value={documentContext}
          onChange={(event) => setDocumentContext(event.target.value)}
          placeholder="Optional context for this file, such as document source, business scenario, supplier hints, known amount range, or special terminology."
        />
      </details>
      <section className="reviewPane sampleReviewPane">
        {selected ? (
          <>
            <div className="panelHeader">
              <div>
                <h2>{selected.file_name}</h2>
                <p>Model: {selected.model}</p>
              </div>
              <button className="primary" onClick={confirm}>
                Confirm
              </button>
            </div>
            <div className="reviewGrid">
              <label>
                Normalized Markdown preview
                <textarea value={selected.raw_text} readOnly aria-label="Normalized Markdown preview" />
              </label>
              <label>
                Corrected JSON
                <textarea value={jsonText} onChange={(event) => setJsonText(event.target.value)} aria-label="Corrected JSON" />
              </label>
            </div>
            <ProcessingTrace trace={selected.trace} />
          </>
        ) : (
          <div className="empty">No document uploaded yet.</div>
        )}
      </section>
    </section>
  );
}

function ExtractedResultsPanel({ workspace, onNotice }: { workspace: Workspace; onNotice: (message: string) => void }) {
  const [results, setResults] = useState<ExtractionResult[]>([]);
  const [selected, setSelected] = useState<ExtractionResult | null>(null);

  useEffect(() => {
    void api.results(workspace.id)
      .then((list) => {
        setResults(list);
        setSelected(list[0] ?? null);
      })
      .catch((error: Error) => onNotice(error.message));
  }, [workspace.id, onNotice]);

  return (
    <section className="panel split">
      <aside className="listPane">
        <div className="panelHeader">
          <div>
            <h2>Extracted Results</h2>
            <p>Read-only view of extraction runs and their processing trace.</p>
          </div>
        </div>
        <div className="resultList">
          {results.map((result) => (
            <button key={result.id} className={selected?.id === result.id ? 'resultItem active' : 'resultItem'} onClick={() => setSelected(result)}>
              <strong>{result.file_name}</strong>
              <span>{result.status.replaceAll('_', ' ')}</span>
            </button>
          ))}
        </div>
      </aside>
      <section className="reviewPane">
        {selected ? (
          <>
            <div className="panelHeader">
              <div>
                <h2>{selected.file_name}</h2>
                <p>Model: {selected.model}</p>
              </div>
            </div>
            <div className="reviewGrid">
              <label>
                Normalized Markdown preview
                <textarea value={selected.raw_text} readOnly aria-label="Normalized Markdown preview" />
              </label>
              <label>
                Extracted JSON
                <textarea value={JSON.stringify(hasPayload(selected.corrected_data) ? selected.corrected_data : selected.extracted_data, null, jsonIndent)} readOnly aria-label="Extracted JSON" />
              </label>
            </div>
            <ProcessingTrace trace={selected.trace} />
          </>
        ) : (
          <div className="empty">No extraction result yet.</div>
        )}
      </section>
    </section>
  );
}

function IntegrationPanel({ workspace, onNotice }: { workspace: Workspace; onNotice: (message: string) => void }) {
  const [integrations, setIntegrations] = useState<IntegrationWorkflow[]>([]);
  const [current, setCurrent] = useState<IntegrationWorkflow | null>(null);
  const [jsonTarget, setJsonTarget] = useState('{}');
  const [variableText, setVariableText] = useState('');

  const load = async () => {
    const list = await api.integrations(workspace.id);
    setIntegrations(list);
    setCurrent((item) => (item ? list.find((entry) => entry.id === item.id) ?? list[0] ?? null : list[0] ?? null));
  };

  useEffect(() => {
    void load().catch((error: Error) => onNotice(error.message));
  }, [workspace.id]);

  useEffect(() => {
    if (current) {
      setJsonTarget(JSON.stringify(current.config.mapping.target_schema || {}, null, jsonIndent));
      setVariableText(JSON.stringify(current.config.variables || [], null, jsonIndent));
    }
  }, [current?.id]);

  const create = async () => {
    try {
      const item = await api.createIntegration(workspace.id, 'New integration', emptyIntegrationConfig());
      setCurrent(item);
      await load();
    } catch (error) {
      onNotice((error as Error).message);
    }
  };

  const save = async (config: IntegrationConfig, name = current?.name ?? 'Integration') => {
    if (!current) return;
    try {
      const item = await api.updateIntegration(current.id, { name, config });
      setCurrent(item);
      await load();
      onNotice('Integration saved.');
    } catch (error) {
      onNotice((error as Error).message);
    }
  };

  const activate = async () => {
    if (!current) return;
    try {
      const item = await api.activateIntegration(current.id);
      setCurrent(item);
      await load();
      onNotice('Integration activated.');
    } catch (error) {
      onNotice((error as Error).message);
    }
  };

  if (!current) {
    return (
      <section className="panel">
        <div className="empty">
          <p>No integration workflow yet.</p>
          <button className="primary" onClick={create}>
            Create Integration
          </button>
        </div>
      </section>
    );
  }

  const config = current.config;
  const patch = (next: Partial<IntegrationConfig>) => ({ ...config, ...next });

  return (
    <section className="panel">
      <div className="panelHeader">
        <div>
          <h2>Integration Workflow</h2>
          <p>Configure File Entrance → Job Scheduler → Mapping → Destination → Activation.</p>
        </div>
        <div className="actions">
          <select value={current.id} onChange={(event) => setCurrent(integrations.find((item) => item.id === event.target.value) ?? current)}>
            {integrations.map((item) => (
              <option key={item.id} value={item.id}>
                {item.name}
              </option>
            ))}
          </select>
          <button onClick={create}>New</button>
          <button className="primary" onClick={activate}>
            Activate
          </button>
        </div>
      </div>
      <div className="workflowTree">
        {[
          { title: 'Start Variables', description: `${config.variables.length} variable(s)`, state: 'active' },
          { title: 'File Entrance', description: config.file_entrance.source_type.replace('_', ' ') },
          { title: 'Job Scheduler', description: config.scheduler.mode },
          { title: 'Mapping', description: `${config.mapping.field_mappings.length} field mapping(s)` },
          { title: 'Destination', description: config.destination.url || 'Not connected' },
          { title: 'Activation', description: current.status === 'active' ? 'Active' : 'Draft', state: current.status === 'active' ? 'active' : 'draft' }
        ].map((item, index) => (
          <ProcessNode key={item.title} index={String(index + 1).padStart(2, '0')} title={item.title} description={item.description} state={item.state as 'active' | 'draft' | undefined} />
        ))}
      </div>
      <div className="workflowGrid">
        <section className="card">
          <h3>Start Variables</h3>
          <textarea value={variableText} onChange={(event) => setVariableText(event.target.value)} />
          <button
            onClick={() => {
              const variables = JSON.parse(variableText) as IntegrationConfig['variables'];
              void save(patch({ variables }));
            }}
          >
            Save Variables
          </button>
        </section>
        <section className="card">
          <h3>File Entrance</h3>
          <FormSelect
            label="Source"
            value={config.file_entrance.source_type}
            options={['manual_upload', 'outlook', 'api', 'shared_folder']}
            onChange={(value) => save(patch({ file_entrance: { ...config.file_entrance, source_type: value as IntegrationConfig['file_entrance']['source_type'] } }))}
          />
          <FormInput label="Account" value={config.file_entrance.account} onChange={(value) => save(patch({ file_entrance: { ...config.file_entrance, account: value } }))} />
          <FormInput label="Folder" value={config.file_entrance.folder} onChange={(value) => save(patch({ file_entrance: { ...config.file_entrance, folder: value } }))} />
          <FormInput label="Sender filter" value={config.file_entrance.sender_contains} onChange={(value) => save(patch({ file_entrance: { ...config.file_entrance, sender_contains: value } }))} />
          <FormInput label="Subject filter" value={config.file_entrance.subject_contains} onChange={(value) => save(patch({ file_entrance: { ...config.file_entrance, subject_contains: value } }))} />
        </section>
        <section className="card">
          <h3>Job Scheduler</h3>
          <FormSelect
            label="Mode"
            value={config.scheduler.mode}
            options={['manual', 'once', 'recurring']}
            onChange={(value) => save(patch({ scheduler: { ...config.scheduler, mode: value as IntegrationConfig['scheduler']['mode'] } }))}
          />
          <FormInput label="Timezone" value={config.scheduler.timezone} onChange={(value) => save(patch({ scheduler: { ...config.scheduler, timezone: value } }))} />
          <FormInput label="Start date" value={config.scheduler.start_date} onChange={(value) => save(patch({ scheduler: { ...config.scheduler, start_date: value } }))} />
          <FormInput label="End date" value={config.scheduler.end_date} onChange={(value) => save(patch({ scheduler: { ...config.scheduler, end_date: value } }))} />
          <FormInput label="Specific times" value={config.scheduler.specific_times.join(', ')} onChange={(value) => save(patch({ scheduler: { ...config.scheduler, specific_times: splitList(value) } }))} />
        </section>
        <section className="card">
          <h3>Mapping</h3>
          <textarea value={jsonTarget} onChange={(event) => setJsonTarget(event.target.value)} />
          <button
            onClick={() => {
              const target = JSON.parse(jsonTarget) as Record<string, unknown>;
              const source = schemaToSource(workspace.schema_info);
              void save(patch({ mapping: { ...config.mapping, source_schema: source, target_schema: target, output_preview: target } }));
            }}
          >
            Import target JSON
          </button>
          <FormInput
            label="Field mappings (source:target)"
            value={config.mapping.field_mappings.map((item) => `${item.source}:${item.target}`).join(', ')}
            onChange={(value) =>
              save(patch({ mapping: { ...config.mapping, field_mappings: splitList(value).map((entry) => {
                const [source, target] = entry.split(':');
                return { source: source?.trim() ?? '', target: target?.trim() ?? '' };
              }) } }))
            }
          />
        </section>
        <section className="card">
          <h3>Destination</h3>
          <FormInput label="Name" value={config.destination.name} onChange={(value) => save(patch({ destination: { ...config.destination, name: value } }))} />
          <FormInput label="URL" value={config.destination.url} onChange={(value) => save(patch({ destination: { ...config.destination, url: value } }))} />
          <FormSelect
            label="Authentication"
            value={config.destination.authentication}
            options={['none', 'basic', 'bearer', 'oauth2']}
            onChange={(value) => save(patch({ destination: { ...config.destination, authentication: value as IntegrationConfig['destination']['authentication'] } }))}
          />
          <FormInput label="Client ID" value={config.destination.client_id} onChange={(value) => save(patch({ destination: { ...config.destination, client_id: value } }))} />
          <FormInput label="Client Secret" value={config.destination.client_secret} onChange={(value) => save(patch({ destination: { ...config.destination, client_secret: value } }))} />
          <FormInput label="Token Service URL" value={config.destination.token_service_url} onChange={(value) => save(patch({ destination: { ...config.destination, token_service_url: value } }))} />
        </section>
      </div>
    </section>
  );
}

function ProcessNode({
  index,
  title,
  description,
  state
}: {
  index: string;
  title: string;
  description: string;
  state?: 'active' | 'draft';
}) {
  return (
    <div className={state ? `processNode ${state}` : 'processNode'}>
      <span>{index}</span>
      <strong>{title}</strong>
      <small>{description}</small>
    </div>
  );
}

function SettingsPanel({ onNotice }: { onNotice: (message: string) => void }) {
  const [settings, setSettings] = useState<ModelSettings>({ provider: 'ollama', base_url: 'http://localhost:11434', model: 'llama3.1' });
  const [models, setModels] = useState<string[]>([]);

  useEffect(() => {
    void Promise.all([api.modelSettings(), api.modelList()])
      .then(([current, list]) => {
        setSettings(current);
        setModels(list);
      })
      .catch((error: Error) => onNotice(error.message));
  }, []);

  const save = async () => {
    try {
      const result = await api.saveModelSettings(settings);
      setSettings(result);
      setModels(await api.modelList());
      onNotice('Model settings saved.');
    } catch (error) {
      onNotice((error as Error).message);
    }
  };

  return (
    <section className="panel narrow">
      <h2>Model Settings</h2>
      <p>Default provider is local Ollama. Switch to mock when a local model is not running.</p>
      <FormSelect
        label="Provider"
        value={settings.provider}
        options={['ollama', 'mock']}
        onChange={(value) => setSettings({ ...settings, provider: value as ModelSettings['provider'] })}
      />
      <FormInput label="Base URL" value={settings.base_url} onChange={(value) => setSettings({ ...settings, base_url: value })} />
      <FormInput label="Model" value={settings.model} onChange={(value) => setSettings({ ...settings, model: value })} />
      {models.length > 0 && (
        <label>
          Available models
          <select value={settings.model} onChange={(event) => setSettings({ ...settings, model: event.target.value })}>
            {models.map((model) => (
              <option key={model}>{model}</option>
            ))}
          </select>
        </label>
      )}
      <button className="primary" onClick={save}>
        Save settings
      </button>
    </section>
  );
}

function FormInput({ label, value, onChange }: { label: string; value: string | number; onChange: (value: string) => void }) {
  return (
    <label>
      {label}
      <input value={value} onChange={(event) => onChange(event.target.value)} />
    </label>
  );
}

function FormSelect({ label, value, options, onChange }: { label: string; value: string; options: string[]; onChange: (value: string) => void }) {
  return (
    <label>
      {label}
      <select value={value} onChange={(event) => onChange(event.target.value)}>
        {options.map((option) => (
          <option key={option} value={option}>
            {option}
          </option>
        ))}
      </select>
    </label>
  );
}

function labelForTab(tab: Tab): string {
  return {
    initialization: 'Expected Output',
    examples: 'Samples',
    prompts: 'Prompt Versions',
    documents: 'Extracted Results',
    integration: 'Integration',
    settings: 'Model Settings',
    processing: 'Processing Settings'
  }[tab];
}

function updateOutputField(fields: SchemaField[], path: number[], patch: Partial<SchemaField>): SchemaField[] {
  const [head, ...tail] = path;
  return fields.map((field, index) => {
    if (index !== head) return field;
    if (tail.length === 0) return { ...field, ...patch };
    return { ...field, children: updateOutputField(field.children ?? [], tail, patch) };
  });
}

function removeOutputField(fields: SchemaField[], path: number[]): SchemaField[] {
  const [head, ...tail] = path;
  if (tail.length === 0) {
    return fields.filter((_, index) => index !== head);
  }
  return fields.map((field, index) => (index === head ? { ...field, children: removeOutputField(field.children ?? [], tail) } : field));
}

function addOutputChild(fields: SchemaField[], path: number[], child: SchemaField): SchemaField[] {
  const [head, ...tail] = path;
  return fields.map((field, index) => {
    if (index !== head) return field;
    if (tail.length === 0) return { ...field, children: [...(field.children ?? []), child] };
    return { ...field, children: addOutputChild(field.children ?? [], tail, child) };
  });
}

function compatibleConstraints(constraints: Record<string, unknown>, type: SchemaField['type']): Record<string, unknown> {
  if (type === 'number') {
    return pickConstraints(constraints, ['min', 'max']);
  }
  if (type === 'string' || type === 'date') {
    return pickConstraints(constraints, ['minLength', 'maxLength', 'exactLength', 'pattern']);
  }
  return {};
}

function pickConstraints(source: Record<string, unknown>, keys: string[]): Record<string, unknown> {
  return keys.reduce<Record<string, unknown>>((result, key) => {
    if (source[key] !== undefined) {
      result[key] = source[key];
    }
    return result;
  }, {});
}

function countOutputFields(schemaInfo: SchemaInfo): number {
  const schema = normalizeExpectedOutputSchema(schemaInfo);
  return countFields(schema.children);
}

function countFields(fields: SchemaField[]): number {
  return fields.reduce((count, field) => {
    if (field.ignored) return count;
    return count + 1 + countFields(field.children ?? []);
  }, 0);
}

function schemaToSource(schemaInfo: SchemaInfo): Record<string, unknown> | Array<Record<string, unknown>> {
  const schema = normalizeExpectedOutputSchema(schemaInfo);
  const source = fieldsToSource(schema.children);
  return schema.outputType === 'jsonArray' ? [source] : source;
}

function fieldsToSource(fields: SchemaField[]): Record<string, unknown> {
  return fields.reduce<Record<string, unknown>>((acc, field) => {
    if (field.ignored) return acc;
    if (field.type === 'json') {
      acc[field.fieldName] = fieldsToSource(field.children ?? []);
    } else if (field.type === 'jsonArray') {
      acc[field.fieldName] = [fieldsToSource(field.children ?? [])];
    } else {
      acc[field.fieldName] = field.type;
    }
    return acc;
  }, {});
}

function hasPayload(value: unknown): boolean {
  if (Array.isArray(value)) return value.length > 0;
  if (value && typeof value === 'object') return Object.keys(value).length > 0;
  return value !== null && value !== undefined && value !== '';
}

function constraintText(value: unknown): string {
  return typeof value === 'string' || typeof value === 'number' ? String(value) : '';
}

function splitList(value: string): string[] {
  return value
    .split(',')
    .map((item) => item.trim())
    .filter(Boolean);
}
