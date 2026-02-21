'use client'
import { useParams, useRouter } from 'next/navigation'
import { useEffect, useState } from 'react'
import { apiFetch } from '@/lib/api'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/Card'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/Table'
import { Badge } from '@/components/ui/Badge'
import { Button } from '@/components/ui/Button'
import { ArrowLeft } from 'lucide-react'
import Link from 'next/link'

interface WorkloadDetail {
  name: string
  kind: string
  namespace: string
  replicas?: number
  ready: number
  images: string[]
  pods: {
    name: string
    phase: string
    restarts: number
  }[]
  conditions: {
    type: string
    status: string
    message: string
  }[]
}

export default function WorkloadDetail() {
  const { kind, ns, name } = useParams()
  const router = useRouter()
  const [workload, setWorkload] = useState<WorkloadDetail | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    if (!kind || !ns || !name) return
    apiFetch<WorkloadDetail>(`/workloads/${kind}/${ns}/${name}`)
      .then(setWorkload)
      .catch(console.error)
      .finally(() => setLoading(false))
  }, [kind, ns, name])

  if (loading) return <div className="p-8 text-center">Loading...</div>
  if (!workload) return <div className="p-8 text-center text-red-500">Workload not found</div>

  return (
    <div className="container mx-auto p-4 space-y-6">
      <div className="flex items-center gap-4">
        <Button variant="ghost" size="icon" onClick={() => router.back()}>
            <ArrowLeft className="h-5 w-5" />
        </Button>
        <h1 className="text-2xl font-bold">{workload.name} <span className="text-muted-foreground text-sm font-normal">({workload.kind})</span></h1>
      </div>

      <div className="grid gap-4 md:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle>Details</CardTitle>
          </CardHeader>
          <CardContent className="space-y-2">
            <div className="flex justify-between border-b pb-2">
               <span className="font-medium">Namespace</span>
               <span>{workload.namespace}</span>
            </div>
            {workload.replicas !== undefined && (
                <div className="flex justify-between border-b pb-2">
                    <span className="font-medium">Replicas</span>
                    <span>{workload.ready} / {workload.replicas}</span>
                </div>
            )}
            <div className="pt-2">
                <span className="font-medium">Images</span>
                <ul className="list-disc pl-5 text-sm mt-1">
                    {workload.images.map((img, i) => <li key={i}>{img}</li>)}
                </ul>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Conditions</CardTitle>
          </CardHeader>
          <CardContent>
            {workload.conditions.length > 0 ? (
                <ul className="space-y-2">
                    {workload.conditions.map((c, i) => (
                        <li key={i} className="border rounded p-2 text-sm">
                            <div className="flex justify-between font-bold">
                                <span>{c.type}</span>
                                <Badge variant={c.status === 'True' ? 'success' : 'secondary'}>{c.status}</Badge>
                            </div>
                            {c.message && <p className="mt-1 text-muted-foreground">{c.message}</p>}
                        </li>
                    ))}
                </ul>
            ) : <p className="text-muted-foreground">No conditions reported</p>}
          </CardContent>
        </Card>
      </div>

      <Card>
        <CardHeader>
            <CardTitle>Pods</CardTitle>
        </CardHeader>
        <CardContent>
             <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Name</TableHead>
                    <TableHead>Status</TableHead>
                    <TableHead>Restarts</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {workload.pods.map((pod) => (
                    <TableRow key={pod.name}>
                      <TableCell>
                         <Link href={`/pods/${ns}/${pod.name}`} className="hover:underline text-primary">
                          {pod.name}
                        </Link>
                      </TableCell>
                      <TableCell>
                        <Badge variant={pod.phase === 'Running' ? 'success' : pod.phase === 'Failed' ? 'destructive' : 'secondary'}>
                          {pod.phase}
                        </Badge>
                      </TableCell>
                      <TableCell>{pod.restarts}</TableCell>
                    </TableRow>
                  ))}
                  {workload.pods.length === 0 && (
                      <TableRow>
                          <TableCell colSpan={3} className="text-center">No pods found matching selector</TableCell>
                      </TableRow>
                  )}
                </TableBody>
              </Table>
        </CardContent>
      </Card>
    </div>
  )
}
