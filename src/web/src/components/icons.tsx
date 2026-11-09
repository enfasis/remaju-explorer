import type { ReactNode } from 'react'

function Icon({ children, size = 16 }: { children: ReactNode; size?: number }) {
  return <svg viewBox="0 0 24 24" width={size} height={size} fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true" focusable="false">{children}</svg>
}

export const SunIcon = () => <Icon><circle cx="12" cy="12" r="4" /><path d="M12 2v2M12 20v2M4.93 4.93l1.41 1.41M17.66 17.66l1.41 1.41M2 12h2M20 12h2M6.34 17.66l-1.41 1.41M19.07 4.93l-1.41 1.41" /></Icon>
export const MoonIcon = () => <Icon><path d="M12 3a6 6 0 0 0 9 9 9 9 0 1 1-9-9Z" /></Icon>
export const HelpIcon = () => <Icon><circle cx="12" cy="12" r="10" /><path d="M9.09 9a3 3 0 0 1 5.83 1c0 2-3 3-3 3M12 17h.01" /></Icon>
export const ChevronIcon = () => <Icon size={14}><path d="m6 9 6 6 6-6" /></Icon>
export const CheckIcon = () => <Icon size={14}><path d="M20 6 9 17l-5-5" /></Icon>
export const ClearFiltersIcon = () => <Icon><path d="M13.01 13 22 3H2l8 9.46V19l4 2v-6.99M17 14l5 5M22 14l-5 5" /></Icon>
export const CloseIcon = () => <Icon><path d="M18 6 6 18M6 6l12 12" /></Icon>
export const GitHubIcon = () => <svg viewBox="0 0 24 24" width="16" height="16" fill="currentColor" aria-hidden="true" focusable="false"><path d="M12 .8a11.2 11.2 0 0 0-3.54 21.83c.56.1.76-.24.76-.54v-2.1c-3.11.67-3.77-1.32-3.77-1.32-.51-1.3-1.25-1.65-1.25-1.65-1.02-.7.08-.69.08-.69 1.13.08 1.73 1.16 1.73 1.16 1 1.72 2.63 1.22 3.27.93.1-.73.39-1.22.7-1.5-2.49-.28-5.11-1.24-5.11-5.54 0-1.23.44-2.23 1.15-3.02-.11-.28-.5-1.42.11-2.97 0 0 .94-.3 3.08 1.15a10.7 10.7 0 0 1 5.6 0c2.14-1.45 3.07-1.15 3.07-1.15.61 1.55.23 2.69.12 2.97.71.79 1.14 1.79 1.14 3.02 0 4.31-2.62 5.25-5.12 5.53.4.35.76 1.03.76 2.08v3.09c0 .3.2.65.77.54A11.2 11.2 0 0 0 12 .8Z" /></svg>
export const PinIcon = () => <Icon><path d="M20 10c0 6-8 12-8 12s-8-6-8-12a8 8 0 0 1 16 0Z" /><circle cx="12" cy="10" r="3" /></Icon>
export const MapIcon = () => <Icon><path d="m3 6 6-3 6 3 6-3v15l-6 3-6-3-6 3ZM9 3v15M15 6v15" /></Icon>
export const DollarIcon = () => <Icon><path d="M12 2v20M17 5H9.5a3.5 3.5 0 0 0 0 7h5a3.5 3.5 0 0 1 0 7H6" /></Icon>
export const LocateIcon = () => <Icon><circle cx="12" cy="12" r="3" /><path d="M12 2v3M12 19v3M2 12h3M19 12h3" /><circle cx="12" cy="12" r="7" /></Icon>
export const DownloadIcon = () => <Icon><path d="M12 3v12M7 10l5 5 5-5M5 21h14" /></Icon>
export const FileIcon = () => <Icon><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8Z" /><path d="M14 2v6h6" /></Icon>
