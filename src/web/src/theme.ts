import { createTamagui } from 'tamagui'
import { animationsCSS } from '@tamagui/config/animations-css'
import { createV6Config } from '@tamagui/config/v6-base'
import { createPaletteThemes } from '@tamagui/config/v6-builder'

export const chavin = { red: '#d7263d', green: '#178a5b', yellow: '#f5c518', blue: '#2d6cdf' }

const { themes, colorTokens } = createPaletteThemes({
  surface: ['#fbfbfa', '#f5f5f3', '#ebeae7', '#dbd9d5', '#b3b0aa', '#8a867f', '#6a665f', '#514e48', '#363431', '#22211f', '#121211'],
  brand: ['#fef2f3', '#fde3e6', '#fbc8cf', '#f79eab', '#f06a7d', '#e53f57', chavin.red, '#b41d32', '#96192c', '#7d1a2b', '#450812'],
  green: ['#effaf5', '#d8f3e6', '#b3e6cf', '#7fd2b0', '#48b78c', '#25996f', chavin.green, '#126e4a', '#11583d', '#0f4833', '#06281c'],
  yellow: ['#fffbea', '#fff3c4', '#ffe78a', '#ffd84d', chavin.yellow, '#dba90c', '#b58407', '#8f610b', '#764d10', '#644013', '#3a2106'],
  blue: ['#eff5ff', '#dbe8fe', '#bfd6fe', '#93bbfd', '#609afa', '#3b7cf4', chavin.blue, '#2357c2', '#22489d', '#21407c', '#18284b'],
})

const base = createV6Config({ themes, colorTokens })
const family = 'Inter, system-ui, sans-serif'

export const config = createTamagui({ ...base, fonts: { body: { ...base.fonts.body, family }, heading: { ...base.fonts.heading, family } }, animations: animationsCSS })

type AppConfig = typeof config

declare module 'tamagui' {
  interface TamaguiCustomConfig extends AppConfig {}
}
