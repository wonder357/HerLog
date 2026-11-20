import { request } from './httpClient'
import type { LoginResult, MemberInfo } from './types'

export interface AuthOptions { sms_mode: 'disabled' | 'demo' | 'live'; requires_phone: boolean }
export interface SmsChallenge { challenge_id: string; expires_in: number; resend_in: number; demo_code?: string }
export type SmsPurpose = 'login' | 'register' | 'bind'
export interface PhoneProof { phone: string; challenge_id: string; code: string }

export const fetchAuthOptions = () => request<AuthOptions>('/auth/options', { anonymous: true })
export const requestSmsCode = (phone: string, purpose: SmsPurpose) =>
  purpose === 'bind'
    ? request<SmsChallenge>('/auth/phone-binding/code', { method: 'POST', data: { phone } })
    : request<SmsChallenge>('/auth/sms-code', { method: 'POST', data: { phone, purpose }, anonymous: true })
export const loginByPhone = (proof: PhoneProof) =>
  request<LoginResult>('/auth/phone-login', { method: 'POST', data: { ...proof }, anonymous: true })
export const registerByPhone = (proof: PhoneProof, username: string, password: string) =>
  request<LoginResult>('/auth/phone-register', { method: 'POST', data: { ...proof, username, password }, anonymous: true })
export const bindPhone = (proof: PhoneProof, password: string) =>
  request<MemberInfo>('/auth/phone-binding', { method: 'POST', data: { ...proof, password } })

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
