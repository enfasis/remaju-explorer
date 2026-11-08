import type { ReactElement } from 'react'
import { Button, TooltipSimple } from 'tamagui'

type Props = { label: string; icon: ReactElement; onPress?: () => void; href?: string; pressed?: boolean; controls?: string; haspopup?: 'dialog' }

export default function IconButton({ label, icon, onPress, href, pressed, controls, haspopup }: Props) {
  return <TooltipSimple label={label} placement="bottom" delay={{ open: 300, close: 0 }}>
    <Button
      size="sm"
      rounded={6}
      variant="quiet"
      icon={icon}
      aria-label={label}
      aria-pressed={pressed}
      aria-controls={controls}
      aria-haspopup={haspopup}
      onPress={onPress}
      render={href ? <a href={href} target="_blank" rel="noreferrer" /> : undefined}
      className="icon-button"
    />
  </TooltipSimple>
}
