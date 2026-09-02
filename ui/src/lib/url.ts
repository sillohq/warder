import { router } from '@inertiajs/react'

/**
 * Every part of a list's state lives in the query string.
 *
 * Not an implementation detail: a filtered, sorted, paged list you cannot send
 * to a colleague is one you rebuild by hand every morning. So changing a filter
 * is a visit to a URL, the back button works, and a bookmark is a saved view.
 */
export function go(patch: Record<string, string | number | null | undefined>, options: { replace?: boolean; only?: string[] } = {}) {
  const url = new URL(window.location.href)
  for (const [key, value] of Object.entries(patch)) {
    if (value === null || value === undefined || value === '') url.searchParams.delete(key)
    else url.searchParams.set(key, String(value))
  }
  // Any change to what is shown resets to the first page, because page 7 of a
  // freshly filtered list is almost never where you wanted to be.
  if (!('page' in patch)) url.searchParams.delete('page')
  router.visit(url.pathname + url.search, {
    preserveState: true,
    preserveScroll: true,
    replace: options.replace ?? false,
    only: options.only,
  })
}

/** The next sort term for a column header click: asc, then desc, then off. */
export function nextSort(current: string[], field: string): string | null {
  const ascending = field
  const descending = `-${field}`
  if (current.includes(ascending)) return descending
  if (current.includes(descending)) return null
  return ascending
}

export function sortDirection(current: string[], field: string | null): 'asc' | 'desc' | null {
  if (!field) return null
  if (current.includes(field)) return 'asc'
  if (current.includes(`-${field}`)) return 'desc'
  return null
}
