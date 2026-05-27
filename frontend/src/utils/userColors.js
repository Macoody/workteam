export const USER_COLOR_OPTIONS = [
  { name: 'Sky', value: '#93c5fd' },
  { name: 'Mint', value: '#86efac' },
  { name: 'Peach', value: '#fdba74' },
  { name: 'Rose', value: '#fda4af' },
  { name: 'Lavender', value: '#c4b5fd' },
  { name: 'Sand', value: '#fcd34d' },
  { name: 'Teal', value: '#5eead4' },
  { name: 'Slate', value: '#cbd5e1' }
]

export function getUserColor(color) {
  return color || '#93c5fd'
}

export function getUserColorStyle(color) {
  return {
    '--user-color': getUserColor(color)
  }
}
