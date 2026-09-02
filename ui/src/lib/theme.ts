/**
 * Light or dark, chosen by the viewer and remembered.
 *
 * Python emits both palettes into the document — light on bare `:root`, dark
 * under both `prefers-color-scheme` and `[data-theme="dark"]` — so switching is
 * one attribute and never a reload. The choice lives in localStorage because it
 * belongs to this browser and not to the account: the same person on a laptop
 * at night and a projector in a meeting wants different answers.
 */
const KEY = 'warder.theme'
type Mode = 'light' | 'dark' | 'system'

export function readMode(): Mode {
  try {
    const stored = localStorage.getItem(KEY)
    if (stored === 'light' || stored === 'dark' || stored === 'system') return stored
  } catch {
    // Private windows and blocked site data both throw. The default is fine.
  }
  return 'system'
}

export function applyMode(mode: Mode) {
  const root = document.documentElement
  if (mode === 'system') root.removeAttribute('data-theme')
  else root.setAttribute('data-theme', mode)
  try {
    localStorage.setItem(KEY, mode)
  } catch {
    // Nothing to do: the page is already showing the right thing.
  }
}

export function resolved(mode: Mode): 'light' | 'dark' {
  if (mode !== 'system') return mode
  return window.matchMedia?.('(prefers-color-scheme: dark)').matches ? 'dark' : 'light'
}

export function nextMode(mode: Mode): Mode {
  return mode === 'dark' ? 'light' : 'dark'
}

export type { Mode }
