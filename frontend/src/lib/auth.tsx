'use client'
import { createContext, useContext, useEffect, useState } from 'react'
import { apiFetch } from './api'
import { useRouter, usePathname } from 'next/navigation'

export interface User {
  id: string
  email: string
  role: string
  allowed_namespaces: string[]
  theme_pref: string
}

interface AuthContextType {
  user: User | null
  loading: boolean
  login: (formData: FormData) => Promise<void>
  logout: () => Promise<void>
}

const AuthContext = createContext<AuthContextType | null>(null)

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<User | null>(null)
  const [loading, setLoading] = useState(true)
  const router = useRouter()
  const pathname = usePathname()

  useEffect(() => {
    checkUser()
  }, [])

  async function checkUser() {
    try {
      const u = await apiFetch<User>('/auth/me')
      setUser(u)
    } catch (e) {
      setUser(null)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    if (!loading) {
      if (!user && pathname !== '/login') {
        router.push('/login')
      } else if (user && pathname === '/login') {
        router.push('/')
      }
    }
  }, [user, loading, pathname, router])

  async function login(formData: FormData) {
    const res = await fetch('/api/auth/login', {
      method: 'POST',
      body: formData,
    })
    if (!res.ok) throw new Error('Login failed')
    await checkUser()
    router.push('/')
  }

  async function logout() {
    await fetch('/api/auth/logout', { method: 'POST' })
    setUser(null)
    router.push('/login')
  }

  if (loading) {
      return <div className="flex h-screen items-center justify-center">Loading...</div>
  }

  return (
    <AuthContext.Provider value={{ user, loading, login, logout }}>
      {children}
    </AuthContext.Provider>
  )
}

export function useAuth() {
    const context = useContext(AuthContext)
    if (!context) {
        throw new Error("useAuth must be used within AuthProvider")
    }
    return context
}
