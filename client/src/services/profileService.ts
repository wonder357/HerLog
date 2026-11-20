import { request } from './httpClient'
import type { ProfileInfo } from './types'
import type { PrivatePhotoPayload } from './privatePhotoService'

export interface ProfilePayload {
  birthday?: string | null
  height_cm?: string | null
  contact_phone?: string | null
  avatar?: PrivatePhotoPayload | null
}

export function getProfile(): Promise<ProfileInfo> {
  return request<ProfileInfo>('/herlog/profile')
}

export function updateProfile(payload: ProfilePayload): Promise<ProfileInfo> {
  return request<ProfileInfo>('/herlog/profile', { method: 'PUT', data: payload })
}
