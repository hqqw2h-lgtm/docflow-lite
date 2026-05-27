export function JsonView({ value, maxHeight = 360 }: { value: unknown; maxHeight?: number }) {
  const text = (() => {
    try {
      return JSON.stringify(value ?? null, null, 2);
    } catch {
      return String(value);
    }
  })();
  return (
    <pre
      style={{
        background: '#fafafa',
        border: '1px solid #f0f0f0',
        borderRadius: 6,
        padding: 12,
        margin: 0,
        maxHeight,
        overflow: 'auto',
        fontSize: 12,
      }}
    >
      {text}
    </pre>
  );
}
