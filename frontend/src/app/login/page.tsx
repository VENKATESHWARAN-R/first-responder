'use client'
import { useState } from 'react'
import { useAuth } from '@/lib/auth'
import { Button } from '@/components/ui/Button'
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/Card'

export default function LoginPage() {
  const { login } = useAuth()
  const [error, setError] = useState('')

  async function handleSubmit(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault()
    setError('')
    const formData = new FormData(e.currentTarget)
    try {
      await login(formData)
    } catch (err) {
      setError('Invalid credentials')
    }
  }

  return (
    <div className="flex min-h-screen items-center justify-center bg-gray-50">
      <Card className="w-full max-w-md">
        <CardHeader>
          <CardTitle className="text-center">Sign In</CardTitle>
        </CardHeader>
        <CardContent>
          <form onSubmit={handleSubmit} className="space-y-4">
            <div>
              <label className="block text-sm font-medium">Email</label>
              <input name="username" type="email" required className="mt-1 block w-full rounded-md border p-2 text-foreground bg-background" />
            </div>
            <div>
              <label className="block text-sm font-medium">Password</label>
              <input name="password" type="password" required className="mt-1 block w-full rounded-md border p-2 text-foreground bg-background" />
            </div>
            {error && <p className="text-red-500 text-sm">{error}</p>}
            <Button type="submit" className="w-full">Login</Button>
          </form>
        </CardContent>
      </Card>
    </div>
  )
}
