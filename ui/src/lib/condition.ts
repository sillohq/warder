import type { ConditionSpec, Json } from '../types'

/**
 * Evaluate a `When` against the form's current values.
 *
 * The same rules as `When.holds` in Python, and the server re-checks it before
 * a write — so a field the condition says is not on the form cannot be saved by
 * anyone who edits the request. This copy exists so the field appears the
 * instant another field changes, rather than after a round trip.
 */
export function holds(condition: ConditionSpec | null | undefined, values: Record<string, Json>): boolean {
  if (!condition) return true
  const inner = condition.conditions.filter(Boolean) as ConditionSpec[]

  switch (condition.test) {
    case 'any':
      return inner.some((c) => holds(c, values))
    case 'all':
      return inner.every((c) => holds(c, values))
    case 'not':
      return !holds(inner[0], values)
  }

  const current = condition.field ? values[condition.field] : undefined
  switch (condition.test) {
    case 'equals':
      return current === condition.value
    case 'not_equals':
      return current !== condition.value
    case 'any_of':
      return Array.isArray(condition.value) && condition.value.includes(current as Json)
    case 'none_of':
      return Array.isArray(condition.value) && !condition.value.includes(current as Json)
    case 'is_true':
      return Boolean(current)
    case 'is_false':
      return !current
    case 'empty':
      return isEmpty(current)
    default:
      return !isEmpty(current)
  }
}

function isEmpty(value: unknown): boolean {
  if (value === null || value === undefined || value === '') return true
  if (Array.isArray(value)) return value.length === 0
  if (typeof value === 'object') return Object.keys(value as object).length === 0
  return false
}
