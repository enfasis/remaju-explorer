import { useEffect } from 'react'

export const siteTitle = 'remaju^mm | Remates judiciales del Perú'

export function useTitle(title?: string | null) {
  useEffect(() => {
    document.title = title ? `${title} | remaju^mm` : siteTitle
    return () => { document.title = siteTitle }
  }, [title])
}
