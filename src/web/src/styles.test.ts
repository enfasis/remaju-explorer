import { describe, expect, it } from 'vitest'
import { readFileSync } from 'node:fs'

const styles = readFileSync(new URL('./styles.css', import.meta.url), 'utf8')

function rule(selector: string): string {
  const start = styles.indexOf(`${selector} {`)
  if (start < 0) throw new Error(`Missing style rule: ${selector}`)
  return styles.slice(start, styles.indexOf('}', start) + 1)
}

describe('explorer surfaces', () => {
  it('uses a transparent navigation background with the requested blur', () => {
    expect(rule('.header')).toContain('background: transparent')
    expect(rule('.header')).toContain('backdrop-filter: blur(2px)')
    expect(styles).not.toContain('.header { background: var(--base)')
  })

  it('uses the requested pattern opacity without dimming the source SVG again', () => {
    expect(rule('body::before')).toContain('opacity: .025')
    expect(rule('body::before')).toContain('#000 0 15%, transparent 75%')
    expect(rule('body::before')).toContain('--pattern-x1')
    expect(rule('body::before')).toContain('--pattern-x2')
    expect(styles).not.toContain("%3Cg opacity=")
  })

  it('matches the borderless white table headers to the controls, with a focus-only field ring', () => {
    expect(rule(':root')).toContain('--base: #fff')
    expect(rule(':root')).toContain('--radius: 4px')
    expect(rule(':root')).toContain('--field: #fff')
    expect(rule(':root')).toContain('--control-text: #374151')
    expect(rule(':root')).toContain('--control-border: #e5e7eb')
    expect(rule('.field-frame')).toContain('border: 0')
    expect(rule('.field-frame:focus-within')).toContain('outline: 2px solid color-mix(in srgb, var(--icon-blue) 20%, transparent)')
    expect(rule('.auction-table thead th')).toContain('background: var(--field)')
    expect(rule('.auction-table thead th')).toContain('border: 0')
    expect(rule('.auction-table thead')).toContain('font-size: .8rem')
    expect(rule('.auction-table thead button')).toContain('font-weight: 300')
    expect(rule('.auction-table thead button')).toContain('color: var(--placeholder)')
    expect(rule('.auction-table thead th')).not.toContain('border-left:')
    expect(rule('.auction-table thead th')).not.toContain('border-right:')
  })

  it('uses smaller muted placeholders without shrinking entered text', () => {
    expect(rule(':root')).toContain('--placeholder: #6b7280')
    expect(rule(':root[data-theme="dark"]')).toContain('--placeholder: #9ca3af')
    expect(rule('.field .placeholder')).toContain('font-size: .8rem')
    expect(rule('.filters input.field::placeholder, .results-bar input.field::placeholder')).toContain('font-size: .8rem')
    expect(rule('.field-frame .field')).not.toContain('font-size:')
  })

  it('matches the guide to the page with a background-free close icon and an underlined manual link', () => {
    expect(rule('.dialog-panel')).toContain('background: var(--field)')
    expect(rule('.dialog-panel .dialog-heading .icon-button')).toContain('background: transparent')
    expect(rule('.dialog-panel .dialog-heading .icon-button')).toContain('backdrop-filter: none')
    expect(rule('.guide-manual')).toContain('text-decoration: underline')
    expect(rule('.guide-manual')).toContain('color: var(--icon-blue)')
  })
})
