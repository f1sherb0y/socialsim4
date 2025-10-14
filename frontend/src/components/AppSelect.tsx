import * as Select from "@radix-ui/react-select";
import { ReactNode } from "react";

type Option = { value: string; label: string };

export function AppSelect({
  options,
  value,
  placeholder,
  onChange,
  size = "normal",
}: {
  options: Option[];
  value: string;
  placeholder?: string;
  onChange: (value: string) => void;
  size?: "normal" | "small";
}) {
  const label = value || placeholder || (options[0]?.label ?? "");
  const triggerClass = `input fancy-select-trigger${size === "small" ? " small" : ""}`;

  return (
    <Select.Root value={value} onValueChange={onChange}>
      <Select.Trigger className={triggerClass} aria-label={placeholder || "select"} style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: '0.5rem' }}>
        <Select.Value placeholder={label} />
        <span style={{ color: '#94a3b8' }}>▾</span>
      </Select.Trigger>
      <Select.Portal>
        <Select.Content className="card select-dropdown" position="popper" sideOffset={2}>
          <Select.Viewport style={{ display: 'grid', gap: 2 }}>
            {options.map((opt) => (
              <Select.Item key={opt.value} value={opt.value} className="select-option" style={{ textAlign: 'left', border: 'none', padding: '0.16rem 0.28rem', borderRadius: 8, cursor: 'pointer' }}>
                <Select.ItemText>{opt.label}</Select.ItemText>
              </Select.Item>
            ))}
          </Select.Viewport>
        </Select.Content>
      </Select.Portal>
    </Select.Root>
  );
}
