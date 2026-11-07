import type { ReactElement } from 'react'
import { Button, TooltipSimple } from 'tamagui'

type Props = { label: string; icon: ReactElement; onPress?: () => void; href?: string; pressed?: boolean; controls?: string; haspopup?: 'dialog' }

export const softShadow = '0 1px 2px rgba(31, 22, 16, 0.08), 0 2px 6px rgba(31, 22, 16, 0.06)'

export default function IconButton({ label, icon, onPress, href, pressed, controls, haspopup }: Props) {
  return <TooltipSimple label={label} placement="bottom" delay={{ open: 300, close: 0 }}>
    <Button
      size="sm"
      circular
      variant="quiet"
      icon={icon}
      aria-label={label}
      aria-pressed={pressed}
      aria-controls={controls}
      aria-haspopup={haspopup}
      onPress={onPress}
      render={href ? <a href={href} target="_blank" rel="noreferrer" /> : undefined}
      boxShadow={softShadow}
      className="icon-button"
    />
  </TooltipSimple>
}
