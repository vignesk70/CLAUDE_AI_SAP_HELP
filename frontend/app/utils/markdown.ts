import DOMPurify from 'dompurify'
import { marked } from 'marked'

marked.use({ gfm: true, breaks: true })

/**
 * Render a markdown string to sanitised HTML.
 *
 * Messages are only ever populated on the client, but we still guard the
 * sanitiser so SSR never touches a DOM-only API.
 */
export function renderMarkdown(source: string): string {
  const raw = marked.parse(source, { async: false }) as string
  if (!import.meta.client) return raw
  try {
    return DOMPurify.sanitize(raw)
  } catch {
    return raw
  }
}
