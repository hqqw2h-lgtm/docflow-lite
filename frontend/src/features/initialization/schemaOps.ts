import type { OutputFieldType, SchemaField, SchemaInfo } from '../../shared/types';

export const STRING_LIKE: OutputFieldType[] = ['string', 'date'];
export const NUMBER_LIKE: OutputFieldType[] = ['number'];

export function updateField(
  fields: SchemaField[],
  path: number[],
  patch: Partial<SchemaField>
): SchemaField[] {
  if (path.length === 0) return fields;
  const [head, ...rest] = path;
  return fields.map((field, index) => {
    if (index !== head) return field;
    if (rest.length === 0) {
      const next = { ...field, ...patch };
      if (patch.type && patch.type !== field.type) {
        if (patch.type === 'json' || patch.type === 'jsonArray') {
          next.children = field.children ?? [];
        } else {
          next.children = undefined;
        }
        next.constraints = compatibleConstraints(field.constraints ?? {}, patch.type);
      }
      return next;
    }
    return { ...field, children: updateField(field.children ?? [], rest, patch) };
  });
}

export function removeField(fields: SchemaField[], path: number[]): SchemaField[] {
  if (path.length === 0) return fields;
  const [head, ...rest] = path;
  if (rest.length === 0) {
    return fields.filter((_, index) => index !== head);
  }
  return fields.map((field, index) =>
    index === head ? { ...field, children: removeField(field.children ?? [], rest) } : field
  );
}

export function addChild(fields: SchemaField[], path: number[], child: SchemaField): SchemaField[] {
  if (path.length === 0) return [...fields, child];
  const [head, ...rest] = path;
  return fields.map((field, index) =>
    index === head ? { ...field, children: addChild(field.children ?? [], rest, child) } : field
  );
}

export function compatibleConstraints(
  source: Record<string, unknown>,
  type: OutputFieldType
): Record<string, unknown> {
  const keepCommon = ['pattern'];
  if (STRING_LIKE.includes(type)) {
    return pick(source, [...keepCommon, 'minLength', 'maxLength', 'exactLength']);
  }
  if (NUMBER_LIKE.includes(type)) {
    return pick(source, [...keepCommon, 'min', 'max']);
  }
  return pick(source, keepCommon);
}

function pick(source: Record<string, unknown>, keys: string[]): Record<string, unknown> {
  const out: Record<string, unknown> = {};
  for (const key of keys) {
    if (source[key] !== undefined && source[key] !== '') out[key] = source[key];
  }
  return out;
}

export function countFields(fields: SchemaField[]): number {
  return fields.reduce(
    (total, field) =>
      total + 1 + (field.type === 'json' || field.type === 'jsonArray' ? countFields(field.children ?? []) : 0),
    0
  );
}

export function findField(fields: SchemaField[], path: number[]): SchemaField | null {
  if (path.length === 0) return null;
  const [head, ...rest] = path;
  const field = fields[head];
  if (!field) return null;
  if (rest.length === 0) return field;
  return findField(field.children ?? [], rest);
}

export function isSchemaInfoArray(schemaInfo: SchemaInfo): boolean {
  return !Array.isArray(schemaInfo) && schemaInfo.outputType === 'jsonArray';
}
