export function useFormat() {
  function formatDate(value?: string | null): string {
    if (!value) return '—'
    const d = new Date(value)
    if (isNaN(d.getTime())) return '—'
    return d.toLocaleDateString('zh-CN', {
      year: 'numeric',
      month: '2-digit',
      day: '2-digit',
    })
  }

  function formatDateTime(value?: string | null): string {
    if (!value) return '—'
    const d = new Date(value)
    if (isNaN(d.getTime())) return '—'
    return d.toLocaleString('zh-CN', {
      year: 'numeric',
      month: '2-digit',
      day: '2-digit',
      hour: '2-digit',
      minute: '2-digit',
    })
  }

  function formatSize(bytes?: number | null): string {
    if (!bytes && bytes !== 0) return '—'
    if (bytes < 1024) return `${bytes} B`
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
    return `${(bytes / 1024 / 1024).toFixed(2)} MB`
  }

  function shortId(id?: string): string {
    if (!id) return '—'
    return id.slice(0, 8).toUpperCase()
  }

  return { formatDate, formatDateTime, formatSize, shortId }
}
