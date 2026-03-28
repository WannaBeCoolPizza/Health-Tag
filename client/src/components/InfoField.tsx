interface InfoFieldProps {
  label: string;
  value?: string | string[];
  isList?: boolean;
}

export default function InfoField({ label, value, isList = false }: InfoFieldProps) {
  if (!value || (Array.isArray(value) && value.length === 0)) {
    return null;
  }

  if (isList && Array.isArray(value)) {
    return (
      <div className="field">
        <div className="fl">{label}</div>
        <ul className="flist">
          {value.map((item) => (
            <li key={item}>{item}</li>
          ))}
        </ul>
      </div>
    );
  }

  return (
    <div className="field">
      <div className="fl">{label}</div>
      <div className="fv">{String(value)}</div>
    </div>
  );
}
