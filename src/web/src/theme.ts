import { createTamagui } from 'tamagui'
import { animationsCSS } from '@tamagui/config/animations-css'
import { createV6Config } from '@tamagui/config/v6-base'
import { createPaletteThemes } from '@tamagui/config/v6-builder'

export const chavin = { red: '#c73a3a', green: '#4f8a61', yellow: '#d6a437', blue: '#3558a8', teal: '#2e8b87', terra: '#b8613c' }

const { themes, colorTokens } = createPaletteThemes({
  surface: ['#fffdfc', '#f6f3ee', '#f1ece5', '#e4ddd3', '#c8beb1', '#8a8178', '#6a625b', '#544b43', '#3a322b', '#24211e', '#1c1a18'],
  brand: ['#fdf2f0', '#f7e0dc', '#edc1bb', '#e39c93', '#d97b70', '#d05a50', chavin.red, '#aa3030', '#8f2727', '#742323', '#471313'],
  green: ['#f1f7f1', '#dceedf', '#bdddc5', '#9ccbaa', '#7bb38b', '#629e74', chavin.green, '#3d7850', '#2e6a46', '#255238', '#172f21'],
  yellow: ['#fcf8ec', '#f4e5be', '#ebd394', '#dfbc62', chavin.yellow, '#ba8b2b', '#9d7222', '#8b5b12', '#6f4912', '#593b13', '#33230d'],
  blue: ['#f0f3fa', '#dde5f8', '#bccced', '#99b0df', '#7692ce', '#5474bd', chavin.blue, '#2f4f93', '#29437a', '#23385f', '#172338'],
})

export const config = createTamagui({ ...createV6Config({ themes, colorTokens }), animations: animationsCSS })

type AppConfig = typeof config

declare module 'tamagui' {
  interface TamaguiCustomConfig extends AppConfig {}
}
