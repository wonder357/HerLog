import { defineStore } from 'pinia'
import { fetchMe, login as loginApi, logout as logoutApi, register as registerApi } from '../services/authService'
import { clearSession, getMember, getToken, saveSession, touchMember } from '../services/httpClient'
import type { LoginResult, MemberInfo } from '../services/types'

interface AuthState {
  token: string
  member: MemberInfo | null
  restoring: boolean
}

export const useAuthStore = defineStore('auth', {
  state: (): AuthState => ({
    token: getToken(),
    member: getMember(),
    restoring: false
  }),
  getters: {
    isLoggedIn: (state) => Boolean(state.token),
    username: (state) => state.member?.username ?? ''
  },
  actions: {
    applyLoginResult(result: LoginResult) {
      saveSession(result)
      this.token = result.token
      this.member = {
        customer_id: result.customer_id,
        username: result.username,
        name: result.name,
        phone: result.phone,
        avatar: result.avatar ?? null,
        org_id: result.org_id ?? null,
        org_ids: result.org_ids ?? []
      }
    },
    restore() {
      this.token = getToken()
      this.member = getMember()
    },
    /** 刷新页面后用 /auth/me 恢复本地用户名身份。 */
    async refresh() {
      if (!this.token) {
        return
      }
      this.restoring = true
      try {
        const member = await fetchMe()
        this.member = member
        touchMember(member)
      } finally {
        this.restoring = false
      }
    },
    async login(username: string, password: string) {
      const result = await loginApi(username, password)
      this.applyLoginResult(result)
      return result
    },
    register(username: string, password: string) {
      return registerApi(username, password)
    },
    async logout() {
      try {
        await logoutApi()
      } catch {
        // 退出以本地清除为准，网络失败不阻塞回到登录页。
      }
      clearSession()
      this.token = ''
      this.member = null
    }
  }
})
