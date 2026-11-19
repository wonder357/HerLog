import { request } from './httpClient'
import type { LoginResult, MemberInfo } from './types'

export function register(username: string, password: string): Promise<{ username: string }> {
  return request<{ username: string }>('/auth/username-register', {
    method: 'POST',
    data: { username, password },
    anonymous: true
  })
}

export function login(username: string, password: string): Promise<LoginResult> {
  return request<LoginResult>('/auth/username-login', {
    method: 'POST',
    data: { username, password },
    anonymous: true
  })
}

export function fetchMe(): Promise<MemberInfo> {
  return request<MemberInfo>('/auth/me')
}

export function logout(): Promise<null> {
  return request<null>('/auth/logout', { method: 'POST', timeout: 3500 })
}
