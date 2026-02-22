'use client'
import { useParams, useRouter } from 'next/navigation'
import { useEffect, useState } from 'react'
import { apiFetch } from '@/lib/api'
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/Card'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/Table'
import { Badge } from '@/components/ui/Badge'
import { Button } from '@/components/ui/Button'
import { ArrowLeft, AlertTriangle, CheckCircle, Clock } from 'lucide-react'
import Link from 'next/link'

interface Container {
  name: string
  state: string
  ready: boolean
  restartCount: number
  reason?: string
  message?: string
  image: string
}

interface PodDetail {
  name: string
  namespace: string
  node: string
  phase: string
  startTime: string
  containers: Container[]
  events: any[]
  diagnosis?: string
}

export default function PodDetailPage() {
  const { ns, name } = useParams()
  const router = useRouter()
  const [pod, setPod] = useState<PodDetail | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    if (!ns || !name) return
    apiFetch<PodDetail>(`/pods/${ns}/${name}`)
      .then(setPod)
      .catch((err) => {
        console.error(err)
        // Optionally redirect or show error
      })
      .finally(() => setLoading(false))
  }, [ns, name])

  if (loading) return <div className="p-8 text-center">Loading...</div>
  if (!pod) return <div className="p-8 text-center text-red-500">Pod not found</div>

  return (
    <div className="container mx-auto p-4 space-y-6">
      <div className="flex items-center gap-4">
        <Button variant="ghost" size="icon" onClick={() => router.back()}>
            <ArrowLeft className="h-5 w-5" />
        </Button>
        <h1 className="text-2xl font-bold">{pod.name}</h1>
        <Badge variant={pod.phase === 'Running' ? 'success' : pod.phase === 'Failed' ? 'destructive' : 'warning'}>
          {pod.phase}
        </Badge>
      </div>

      {pod.diagnosis && (
        <Card className="border-red-500 bg-red-50 dark:bg-red-900/20">
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-red-600 dark:text-red-400">
              <AlertTriangle className="h-5 w-5" />
              Diagnosis: Likely Cause
            </CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-lg font-medium">{pod.diagnosis}</p>
          </CardContent>
        </Card>
      )}

      <div className="grid gap-4 md:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle>Details</CardTitle>
          </CardHeader>
          <CardContent className="space-y-2">
            <div className="flex justify-between border-b pb-2">
              <span className="font-medium">Namespace</span>
              <span>{pod.namespace}</span>
            </div>
            <div className="flex justify-between border-b pb-2">
              <span className="font-medium">Node</span>
              <span>{pod.node}</span>
            </div>
            <div className="flex justify-between border-b pb-2">
              <span className="font-medium">Start Time</span>
              <span>{new Date(pod.startTime).toLocaleString()}</span>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Containers</CardTitle>
          </CardHeader>
          <CardContent>
            {pod.containers.map((c) => (
              <div key={c.name} className="mb-4 last:mb-0 border rounded p-3">
                <div className="flex justify-between items-center mb-2">
                  <span className="font-bold">{c.name}</span>
                  <Badge variant={c.ready ? 'success' : 'secondary'}>{c.state}</Badge>
                </div>
                <div className="text-sm space-y-1">
                  <p>Image: {c.image}</p>
                  <p>Restarts: {c.restartCount}</p>
                  {c.reason && <p className="text-red-500">Reason: {c.reason}</p>}
                  {c.message && <p className="text-xs text-muted-foreground break-all">{c.message}</p>}
                </div>
              </div>
            ))}
          </CardContent>
        </Card>
      </div>

       <Card>
            <CardHeader>
                <CardTitle>Events</CardTitle>
            </CardHeader>
            <CardContent>
                 <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Type</TableHead>
                    <TableHead>Reason</TableHead>
                    <TableHead>Message</TableHead>
                    <TableHead>Count</TableHead>
                    <TableHead>Last Seen</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {pod.events?.map((e, i) => (
                    <TableRow key={i}>
                      <TableCell>
                        <Badge variant={e.type === 'Warning' ? 'warning' : 'secondary'}>
                          {e.type}
                        </Badge>
                      </TableCell>
                      <TableCell>{e.reason}</TableCell>
                      <TableCell className="max-w-md truncate" title={e.message}>{e.message}</TableCell>
                      <TableCell>{e.count}</TableCell>
                      <TableCell>{e.lastTimestamp ? new Date(e.lastTimestamp).toLocaleString() : '-'}</TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </CardContent>
       </Card>
    </div>
  )
}
