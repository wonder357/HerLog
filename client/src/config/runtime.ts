/** 业务 API 直连后端；H5 构建通过 VITE_API_BASE_URL 指定地址。 */
const rawBase = (import.meta.env?.VITE_API_BASE_URL ?? '').trim()
export const API_BASE_URL = rawBase.replace(/\/$/, '')

export function apiUrl(path: string): string {
  return `${API_BASE_URL}${path}`
}

export const API_PREFIX = '/api/v1/c'
