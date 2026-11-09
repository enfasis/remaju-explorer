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

  it('keeps the pattern visible at eight percent without dimming the source SVG again', () => {
    expect(rule('body::before')).toContain('opacity: .08')
    expect(rule('body::before')).toContain('#000 0 15%, transparent 75%')
    expect(rule('body::before')).toContain('--pattern-x1')
    expect(rule('body::before')).toContain('--pattern-x2')
    expect(styles).not.toContain("%3Cg opacity=")
  })

  it('uses white controls, neutral text and borders, with a focus-only field ring', () => {
    expect(rule(':root')).toContain('--field: #fff')
    expect(rule(':root')).toContain('--control-text: #374151')
    expect(rule(':root')).toContain('--control-border: #d1d5db')
    expect(rule('.field-frame')).toContain('border: 1px solid var(--control-border)')
    expect(rule('.field-frame:focus-within')).toContain('border-color: var(--icon-blue)')
    expect(rule('.auction-table thead th')).toContain('background: var(--field)')
    expect(rule('.auction-table thead th')).not.toContain('border-left:')
    expect(rule('.auction-table thead th')).not.toContain('border-right:')
  })
})
