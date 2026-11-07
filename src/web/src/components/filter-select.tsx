import { Select } from 'tamagui'
import { CheckIcon, ChevronIcon } from './icons'

type Option = { value: string; label: string }
type Props = { label: string; value: string; options: Option[]; onChange: (value: string) => void }

export function choices(values: string[], all = 'Todos'): Option[] {
  return [{ value: '', label: all }, ...values.map(value => ({ value, label: value }))]
}

export default function FilterSelect({ label, value, options, onChange }: Props) {
  return <Select value={value} onValueChange={next => onChange(String(next ?? ''))} size="sm" zIndex={200000} renderValue={current => options.find(option => option.value === current)?.label}>
    <Select.Trigger aria-label={label} className="field">
      <Select.Value placeholder={label} className={value ? undefined : 'placeholder'} />
      <Select.Icon><ChevronIcon /></Select.Icon>
    </Select.Trigger>
    <Select.Content>
      <Select.Viewport>
        <Select.Group>
          {options.map(option => <Select.Item key={option.value || 'all'} value={option.value}>
            <Select.ItemText>{option.label}</Select.ItemText>
            <Select.ItemIndicator><CheckIcon /></Select.ItemIndicator>
          </Select.Item>)}
        </Select.Group>
      </Select.Viewport>
    </Select.Content>
  </Select>
}
