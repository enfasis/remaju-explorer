import { createTamagui } from 'tamagui'
import { animationsCSS } from '@tamagui/config/animations-css'
import { createV6Config } from '@tamagui/config/v6-base'
import { createPaletteThemes } from '@tamagui/config/v6-builder'

export const chavin = { red: '#d7263d', green: '#178a5b', yellow: '#f5c518', blue: '#2d6cdf', teal: '#188b8a', terra: '#b8613c' }

const { themes, colorTokens } = createPaletteThemes({
  surface: ['#ffffff', '#f5f6f8', '#eceff3', '#dde1e7', '#b6bdc8', '#8993a1', '#59616d', '#414955', '#303640', '#202329', '#15171b'],
  brand: ['#fef2f3', '#fde3e6', '#fbc8cf', '#f79eab', '#f06a7d', '#e53f57', chavin.red, '#b41d32', '#96192c', '#7d1a2b', '#450812'],
  green: ['#effaf5', '#d8f3e6', '#b3e6cf', '#7fd2b0', '#48b78c', '#25996f', chavin.green, '#126e4a', '#11583d', '#0f4833', '#06281c'],
  yellow: ['#fffbea', '#fff3c4', '#ffe78a', '#ffd84d', chavin.yellow, '#dba90c', '#b58407', '#8f610b', '#764d10', '#644013', '#3a2106'],
  blue: ['#eff5ff', '#dbe8fe', '#bfd6fe', '#93bbfd', '#609afa', '#3b7cf4', chavin.blue, '#2357c2', '#22489d', '#21407c', '#18284b'],
})

export const config = createTamagui({ ...createV6Config({ themes, colorTokens }), animations: animationsCSS })

type AppConfig = typeof config

declare module 'tamagui' {
  interface TamaguiCustomConfig extends AppConfig {}
}
