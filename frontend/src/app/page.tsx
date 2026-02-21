'use client'
import { useEffect, useState } from 'react'
import { apiFetch } from '@/lib/api'
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/Card'
import { Badge } from '@/components/ui/Badge'
import { ThemeSwitcher } from '@/components/ThemeSwitcher'
import Link from 'next/link'
import { useAuth } from '@/lib/auth'

interface Namespace {
  name: string
  status: string
  age: string
  health: string
}

export default function Dashboard() {
  const [namespaces, setNamespaces] = useState<Namespace[]>([])
  const { logout } = useAuth()

  useEffect(() => {
    apiFetch<Namespace[]>('/namespaces').then(setNamespaces).catch(console.error)
  }, [])

  return (
    <div className="min-h-screen bg-background text-foreground">
      <div className="container mx-auto p-4 space-y-6">
        <header className="flex justify-between items-center py-4 border-b">
          <h1 className="text-2xl font-bold tracking-tight">Namespace Observatory</h1>
          <div className="flex items-center gap-4">
            <ThemeSwitcher />
            <button onClick={logout} className="text-sm font-medium hover:underline">Logout</button>
          </div>
        </header>

        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
          {namespaces.map((ns) => (
            <Link key={ns.name} href={`/namespaces/${ns.name}`}>
              <Card className="hover:bg-accent/50 transition-colors cursor-pointer h-full">
                <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                  <CardTitle className="text-lg font-medium">
                    {ns.name}
                  </CardTitle>
                  <Badge variant={ns.health === 'Healthy' ? 'success' : ns.health === 'Critical' ? 'destructive' : 'warning'}>
                    {ns.health}
                  </Badge>
                </CardHeader>
                <CardContent>
                  <div className="text-sm font-semibold text-muted-foreground">{ns.status}</div>
                  <p className="text-xs text-muted-foreground mt-2">
                    Created {ns.age ? new Date(ns.age).toLocaleDateString() : 'Unknown'}
                  </p>
                </CardContent>
              </Card>
            </Link>
          ))}
          {namespaces.length === 0 && (
            <div className="col-span-full text-center py-12 text-muted-foreground">
              No namespaces found or you don't have access to any.
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
