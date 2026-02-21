'use client'
import { useParams } from 'next/navigation'
import { useEffect, useState } from 'react'
import { apiFetch } from '@/lib/api'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/Tabs'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/Card'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/Table'
import Link from 'next/link'
import { Badge } from '@/components/ui/Badge'
import { Button } from '@/components/ui/Button'
import { ArrowLeft } from 'lucide-react'

interface Summary {
  name: string
  health: string
  counts: {
    deployments: number
    statefulsets: number
    daemonsets: number
    pods_total: number
    pods_running: number
    pods_failed: number
    pods_pending: number
    restarts: number
  }
}

interface Workload {
  name: string
  ready: number
  desired: number
}

interface Workloads {
  deployments: number
  items: {
    deployments: Workload[]
    statefulsets: Workload[]
    daemonsets: Workload[]
  }
}

interface Pod {
  name: string
  phase: string
  restarts: number
  node: string
  startTime: string
}

interface Event {
  type: string
  reason: string
  message: string
  object: string
  count: number
  time: string
}

export default function NamespaceDetail() {
  const { ns } = useParams()
  const [summary, setSummary] = useState<Summary | null>(null)
  const [workloads, setWorkloads] = useState<Workloads | null>(null)
  const [pods, setPods] = useState<Pod[]>([])
  const [events, setEvents] = useState<Event[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    if (!ns) return
    const fetchData = async () => {
      try {
        const [s, w, p, e] = await Promise.all([
          apiFetch<Summary>(`/namespaces/${ns}/summary`),
          apiFetch<Workloads>(`/namespaces/${ns}/workloads`),
          apiFetch<Pod[]>(`/namespaces/${ns}/pods`),
          apiFetch<Event[]>(`/namespaces/${ns}/events`),
        ])
        setSummary(s)
        setWorkloads(w)
        setPods(p)
        setEvents(e)
      } catch (err) {
        console.error(err)
      } finally {
        setLoading(false)
      }
    }
    fetchData()
  }, [ns])

  if (loading) return <div className="p-8 text-center">Loading...</div>
  if (!summary) return <div className="p-8 text-center text-red-500">Failed to load namespace details</div>

  return (
    <div className="container mx-auto p-4 space-y-6">
      <div className="flex items-center gap-4">
        <Link href="/">
          <Button variant="ghost" size="icon">
            <ArrowLeft className="h-5 w-5" />
          </Button>
        </Link>
        <h1 className="text-2xl font-bold">{summary.name}</h1>
        <Badge variant={summary.health === 'Healthy' ? 'success' : 'destructive'}>
          {summary.health}
        </Badge>
      </div>

      <div className="grid gap-4 md:grid-cols-4">
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium">Pods Status</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">
              {summary.counts.pods_running} / {summary.counts.pods_total}
            </div>
            <p className="text-xs text-muted-foreground">Running / Total</p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium">Failed Pods</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-destructive">
              {summary.counts.pods_failed}
            </div>
            <p className="text-xs text-muted-foreground">Requiring attention</p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium">Restarts</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-orange-500">
              {summary.counts.restarts}
            </div>
            <p className="text-xs text-muted-foreground">Total across all pods</p>
          </CardContent>
        </Card>
        <Card>
            <CardHeader className="pb-2">
                <CardTitle className="text-sm font-medium">Workloads</CardTitle>
            </CardHeader>
            <CardContent>
                <div className="text-2xl font-bold">
                    {summary.counts.deployments + summary.counts.statefulsets + summary.counts.daemonsets}
                </div>
                <p className="text-xs text-muted-foreground">Total controllers</p>
            </CardContent>
        </Card>
      </div>

      <Tabs defaultValue="pods" className="w-full">
        <TabsList>
          <TabsTrigger value="pods">Pods</TabsTrigger>
          <TabsTrigger value="workloads">Workloads</TabsTrigger>
          <TabsTrigger value="events">Events</TabsTrigger>
        </TabsList>

        <TabsContent value="pods">
          <Card>
            <CardContent className="pt-6">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Name</TableHead>
                    <TableHead>Status</TableHead>
                    <TableHead>Restarts</TableHead>
                    <TableHead>Age</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {pods.map((pod) => (
                    <TableRow key={pod.name}>
                      <TableCell className="font-medium">
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
                      <TableCell>{pod.startTime ? new Date(pod.startTime).toLocaleString() : '-'}</TableCell>
                    </TableRow>
                  ))}
                  {pods.length === 0 && (
                      <TableRow>
                          <TableCell colSpan={4} className="text-center">No pods found</TableCell>
                      </TableRow>
                  )}
                </TableBody>
              </Table>
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="workloads">
          <Card>
            <CardContent className="pt-6 space-y-4">
              <h3 className="font-semibold">Deployments</h3>
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Name</TableHead>
                    <TableHead>Ready / Desired</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {workloads?.items.deployments.map((d) => (
                    <TableRow key={d.name}>
                      <TableCell>
                        <Link href={`/workloads/deployments/${ns}/${d.name}`} className="hover:underline text-primary">
                          {d.name}
                        </Link>
                      </TableCell>
                      <TableCell>{d.ready} / {d.desired}</TableCell>
                    </TableRow>
                  ))}
                   {workloads?.items.deployments.length === 0 && (
                      <TableRow>
                          <TableCell colSpan={2} className="text-center">No deployments found</TableCell>
                      </TableRow>
                  )}
                </TableBody>
              </Table>

              <h3 className="font-semibold pt-4">StatefulSets</h3>
              <Table>
                 <TableHeader>
                  <TableRow>
                    <TableHead>Name</TableHead>
                    <TableHead>Ready / Desired</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {workloads?.items.statefulsets.map((s) => (
                    <TableRow key={s.name}>
                      <TableCell>
                         <Link href={`/workloads/statefulsets/${ns}/${s.name}`} className="hover:underline text-primary">
                          {s.name}
                        </Link>
                      </TableCell>
                      <TableCell>{s.ready} / {s.desired}</TableCell>
                    </TableRow>
                  ))}
                   {workloads?.items.statefulsets.length === 0 && (
                      <TableRow>
                          <TableCell colSpan={2} className="text-center">No statefulsets found</TableCell>
                      </TableRow>
                  )}
                </TableBody>
              </Table>
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="events">
          <Card>
            <CardContent className="pt-6">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Type</TableHead>
                    <TableHead>Reason</TableHead>
                    <TableHead>Object</TableHead>
                    <TableHead>Message</TableHead>
                    <TableHead>Last Seen</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {events.map((e, i) => (
                    <TableRow key={i}>
                      <TableCell>
                        <Badge variant={e.type === 'Warning' ? 'warning' : 'secondary'}>
                          {e.type}
                        </Badge>
                      </TableCell>
                      <TableCell>{e.reason}</TableCell>
                      <TableCell>{e.object}</TableCell>
                      <TableCell className="max-w-md truncate" title={e.message}>{e.message}</TableCell>
                      <TableCell>{e.time ? new Date(e.time).toLocaleString() : '-'}</TableCell>
                    </TableRow>
                  ))}
                   {events.length === 0 && (
                      <TableRow>
                          <TableCell colSpan={5} className="text-center">No events found</TableCell>
                      </TableRow>
                  )}
                </TableBody>
              </Table>
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  )
}
