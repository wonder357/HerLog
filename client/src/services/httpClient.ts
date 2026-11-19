import { API_PREFIX, apiUrl } from '../config/runtime'
import type { LoginResult, MemberInfo } from './types'

const TOKEN_KEY = 'herlog.token'
const MEMBER_KEY = 'herlog.member'

export class ApiRequestError extends Error {
  status: number

  constructor(status: number, message: string) {
    super(message)
    this.status = status
  }
}

/** 账号切换后，旧账号的迟到响应不能再写页面。 */
export class StaleSessionError extends Error {
  constructor() {
    super('stale session')
  }
}

let sessionEpoch = 0
let redirecting = false
const privateUrls = new Set<string>()

export function currentEpoch(): number {
  return sessionEpoch
}

function bumpEpoch(): void {
  sessionEpoch += 1
}

export function getToken(): string {
  return (uni.getStorageSync(TOKEN_KEY) as string) || ''
}

export function getMember(): MemberInfo | null {
  const stored = uni.getStorageSync(MEMBER_KEY)
  if (!stored) {
    return null
  }
  if (typeof stored === 'string') {
    try {
      return JSON.parse(stored) as MemberInfo
    } catch {
      return null
    }
  }
  return stored as MemberInfo
}

export function saveSession(result: LoginResult): void {
  clearPrivateCache()
  uni.setStorageSync(TOKEN_KEY, result.token)
  uni.setStorageSync(MEMBER_KEY, result)
}

export function touchMember(member: MemberInfo): void {
  uni.setStorageSync(MEMBER_KEY, member)
}

export function clearSession(): void {
  clearPrivateCache()
  uni.removeStorageSync(TOKEN_KEY)
  uni.removeStorageSync(MEMBER_KEY)
}

export function clearPrivateCache(): void {
  bumpEpoch()
  for (const url of privateUrls) URL.revokeObjectURL(url)
  privateUrls.clear()
}

function toLogin(): void {
  if (redirecting) {
    return
  }
  redirecting = true
  uni.reLaunch({
    url: '/pages/login/index',
    complete: () => {
      redirecting = false
    }
  })
}

interface RequestOptions {
  method?: 'GET' | 'POST' | 'PUT' | 'DELETE'
  data?: Record<string, unknown> | undefined
  /** 匿名入口（注册、登录）遇 401 不跳登录页。 */
  anonymous?: boolean
  responseType?: 'text' | 'arraybuffer'
  timeout?: number
}

interface Envelope<T> {
  code: number
  message: string
  data: T
}

/** 所有业务请求都走这里：带 token、拆信封、401 统一回登录页。 */
export function request<T>(path: string, options: RequestOptions = {}): Promise<T> {
  const epoch = currentEpoch()
  const token = getToken()
  return new Promise<T>((resolve, reject) => {
    uni.request({
      url: apiUrl(`${API_PREFIX}${path}`),
      method: options.method ?? 'GET',
      data: options.data,
      responseType: options.responseType,
      timeout: options.timeout,
      header: token ? { token } : {},
      success: (response) => {
        if (currentEpoch() !== epoch) {
          reject(new StaleSessionError())
          return
        }
        const status = response.statusCode
        const body = response.data as Envelope<T> | Record<string, unknown> | string
        if (status === 401) {
          if (!options.anonymous) {
            clearSession()
            toLogin()
          }
          const message =
            typeof body === 'object' && body !== null && 'message' in body
              ? String((body as { message: string }).message)
              : '登录状态已失效，请重新登录'
          reject(new ApiRequestError(401, message))
          return
        }
        if (typeof body !== 'object' || body === null) {
          reject(new ApiRequestError(status, '服务返回格式不正确'))
          return
        }
        const envelope = body as Envelope<T>
        if (status >= 400 || envelope.code !== 200) {
          reject(new ApiRequestError(status, envelope.message || '请求失败'))
          return
        }
        resolve(envelope.data)
      },
      fail: () => {
        reject(new ApiRequestError(0, '网络连接失败，请检查后端地址或网络'))
      }
    })
  })
}

/** 私有图片：数组缓冲 + 临时对象 URL，页面卸载时调用释放。 */
export function fetchBlobUrl(path: string): Promise<string> {
  const epoch = currentEpoch()
  const token = getToken()
  return new Promise<string>((resolve, reject) => {
    uni.request({
      url: apiUrl(`${API_PREFIX}${path}`),
      method: 'GET',
      responseType: 'arraybuffer',
      header: token ? { token } : {},
      success: (response) => {
        if (currentEpoch() !== epoch) {
          reject(new StaleSessionError())
          return
        }
        if (response.statusCode !== 200) {
          reject(new ApiRequestError(response.statusCode, '图片读取失败'))
          return
        }
        const contentType = Object.entries(response.header ?? {})
          .find(([key]) => key.toLowerCase() === 'content-type')?.[1]
        const mime = typeof contentType === 'string' ? contentType : 'image/jpeg'
        const blob = new Blob([response.data as ArrayBuffer], { type: mime })
        const url = URL.createObjectURL(blob)
        privateUrls.add(url)
        resolve(url)
      },
      fail: () => reject(new ApiRequestError(0, '图片读取失败'))
    })
  })
}

export function releaseBlobUrl(url: string | null): void {
  if (url && url.startsWith('blob:')) {
    privateUrls.delete(url)
    URL.revokeObjectURL(url)
  }
}
