"use client";

import { useCallback, useRef, useState } from "react";

type StressType = "cpu" | "memory" | "io" | "combined" | "crash";

interface IntervalConfig {
  intervalMs: number;
  totalDurationMs: number;
}

export default function Home() {
  const [response, setResponse] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [targetUrl, setTargetUrl] = useState("http://localhost:8000");
  
  // Interval controls
  const [intervalConfig, setIntervalConfig] = useState<IntervalConfig>({
    intervalMs: 3000,
    totalDurationMs: 60000,
  });
  const [runningTask, setRunningTask] = useState<string | null>(null);
  const intervalRef = useRef<NodeJS.Timeout | null>(null);
  const timeoutRef = useRef<NodeJS.Timeout | null>(null);

  const appendLog = (message: string) => {
    const timestamp = new Date().toLocaleTimeString();
    setResponse((prev) => `[${timestamp}] ${message}\n${prev || ""}`);
  };

  const fetchEndpoint = async (endpoint: string) => {
    try {
      const res = await fetch(`${targetUrl}${endpoint}`);
      const data = await res.json();
      return JSON.stringify(data);
    } catch (error) {
      return `Error: ${String(error)}`;
    }
  };

  const pingBackend = async () => {
    setLoading(true);
    const result = await fetchEndpoint("/");
    appendLog(`PING: ${result}`);
    setLoading(false);
  };

  const crashBackend = async () => {
    setLoading(true);
    try {
      await fetch(`${targetUrl}/crash`);
      appendLog("CRASH: Request sent (server should be down)");
    } catch (error) {
      appendLog(`CRASH: Triggered! (Connection lost: ${String(error)})`);
    }
    setLoading(false);
  };

  const runStress = async (type: StressType, params?: Record<string, number>) => {
    setLoading(true);
    let endpoint = "";
    
    switch (type) {
      case "cpu":
        endpoint = `/stress/cpu?duration=${params?.duration || 5}`;
        break;
      case "memory":
        endpoint = `/stress/memory?size_mb=${params?.size_mb || 100}`;
        break;
      case "io":
        endpoint = `/stress/io?duration=${params?.duration || 5}`;
        break;
      case "combined":
        endpoint = `/stress/combined?cpu_duration=${params?.cpu_duration || 3}&memory_mb=${params?.memory_mb || 50}`;
        break;
      case "crash":
        await crashBackend();
        setLoading(false);
        return;
    }
    
    const result = await fetchEndpoint(endpoint);
    appendLog(`${type.toUpperCase()}: ${result}`);
    setLoading(false);
  };

  const releaseMemory = async () => {
    const result = await fetchEndpoint("/stress/memory/release");
    appendLog(`MEMORY RELEASE: ${result}`);
  };

  const startIntervalTask = useCallback((type: StressType, params?: Record<string, number>) => {
    if (runningTask) return;
    
    setRunningTask(type);
    appendLog(`Starting ${type} stress every ${intervalConfig.intervalMs}ms for ${intervalConfig.totalDurationMs / 1000}s`);
    
    // Run immediately
    runStress(type, params);
    
    // Set up interval
    intervalRef.current = setInterval(() => {
      runStress(type, params);
    }, intervalConfig.intervalMs);
    
    // Set up timeout to stop
    timeoutRef.current = setTimeout(() => {
      stopIntervalTask();
      appendLog(`Completed ${type} stress test cycle`);
    }, intervalConfig.totalDurationMs);
  }, [runningTask, intervalConfig, targetUrl]);

  const stopIntervalTask = () => {
    if (intervalRef.current) {
      clearInterval(intervalRef.current);
      intervalRef.current = null;
    }
    if (timeoutRef.current) {
      clearTimeout(timeoutRef.current);
      timeoutRef.current = null;
    }
    setRunningTask(null);
    appendLog("Stopped interval task");
  };

  const clearLogs = () => {
    setResponse(null);
  };

  return (
    <main className="min-h-screen p-8 bg-gray-900 text-white">
      <div className="max-w-4xl mx-auto">
        <h1 className="text-3xl font-bold mb-6 text-center">🔥 Load Testing Dashboard</h1>
        
        {/* Backend URL Config */}
        <div className="mb-6 p-4 bg-gray-800 rounded-lg">
          <label className="block text-sm font-medium mb-2">Backend URL</label>
          <input 
            className="w-full p-2 rounded bg-gray-700 text-white border border-gray-600 focus:border-blue-500 focus:outline-none"
            value={targetUrl} 
            onChange={(e) => setTargetUrl(e.target.value)}
          />
        </div>

        {/* Interval Configuration */}
        <div className="mb-6 p-4 bg-gray-800 rounded-lg">
          <h2 className="text-lg font-semibold mb-3">⏱️ Interval Configuration</h2>
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-sm mb-1">Interval (seconds)</label>
              <select
                className="w-full p-2 rounded bg-gray-700 border border-gray-600"
                value={intervalConfig.intervalMs}
                onChange={(e) => setIntervalConfig(prev => ({ ...prev, intervalMs: Number(e.target.value) }))}
                disabled={!!runningTask}
              >
                <option value={1000}>1s</option>
                <option value={2000}>2s</option>
                <option value={3000}>3s</option>
                <option value={5000}>5s</option>
                <option value={10000}>10s</option>
              </select>
            </div>
            <div>
              <label className="block text-sm mb-1">Total Duration</label>
              <select
                className="w-full p-2 rounded bg-gray-700 border border-gray-600"
                value={intervalConfig.totalDurationMs}
                onChange={(e) => setIntervalConfig(prev => ({ ...prev, totalDurationMs: Number(e.target.value) }))}
                disabled={!!runningTask}
              >
                <option value={30000}>30 seconds</option>
                <option value={60000}>1 minute</option>
                <option value={120000}>2 minutes</option>
                <option value={300000}>5 minutes</option>
              </select>
            </div>
          </div>
        </div>

        {/* Single Action Buttons */}
        <div className="mb-6 p-4 bg-gray-800 rounded-lg">
          <h2 className="text-lg font-semibold mb-3">🎯 Single Actions</h2>
          <div className="flex flex-wrap gap-2">
            <button onClick={pingBackend} disabled={loading} className="px-4 py-2 bg-green-600 hover:bg-green-700 rounded transition disabled:opacity-50">
              Ping
            </button>
            <button onClick={() => runStress("cpu", { duration: 5 })} disabled={loading} className="px-4 py-2 bg-orange-600 hover:bg-orange-700 rounded transition disabled:opacity-50">
              CPU (5s)
            </button>
            <button onClick={() => runStress("memory", { size_mb: 100 })} disabled={loading} className="px-4 py-2 bg-purple-600 hover:bg-purple-700 rounded transition disabled:opacity-50">
              Memory (100MB)
            </button>
            <button onClick={() => runStress("io", { duration: 3 })} disabled={loading} className="px-4 py-2 bg-blue-600 hover:bg-blue-700 rounded transition disabled:opacity-50">
              I/O (3s)
            </button>
            <button onClick={releaseMemory} disabled={loading} className="px-4 py-2 bg-gray-600 hover:bg-gray-700 rounded transition disabled:opacity-50">
              Release Memory
            </button>
            <button onClick={crashBackend} disabled={loading} className="px-4 py-2 bg-red-600 hover:bg-red-700 rounded transition disabled:opacity-50">
              💀 Crash
            </button>
          </div>
        </div>

        {/* Interval Stress Buttons */}
        <div className="mb-6 p-4 bg-gray-800 rounded-lg">
          <h2 className="text-lg font-semibold mb-3">🔄 Interval Stress (Recurring)</h2>
          {runningTask ? (
            <div className="flex items-center gap-4">
              <span className="text-yellow-400 animate-pulse">Running: {runningTask.toUpperCase()}</span>
              <button onClick={stopIntervalTask} className="px-4 py-2 bg-red-600 hover:bg-red-700 rounded transition">
                ⏹ Stop
              </button>
            </div>
          ) : (
            <div className="flex flex-wrap gap-2">
              <button onClick={() => startIntervalTask("cpu", { duration: 3 })} className="px-4 py-2 bg-orange-700 hover:bg-orange-800 rounded transition">
                🔄 CPU Interval
              </button>
              <button onClick={() => startIntervalTask("memory", { size_mb: 50 })} className="px-4 py-2 bg-purple-700 hover:bg-purple-800 rounded transition">
                🔄 Memory Interval
              </button>
              <button onClick={() => startIntervalTask("combined", { cpu_duration: 2, memory_mb: 30 })} className="px-4 py-2 bg-pink-700 hover:bg-pink-800 rounded transition">
                🔄 Combined Interval
              </button>
            </div>
          )}
        </div>

        {/* Response Log */}
        <div className="p-4 bg-gray-800 rounded-lg">
          <div className="flex justify-between items-center mb-3">
            <h2 className="text-lg font-semibold">📋 Response Log</h2>
            <button onClick={clearLogs} className="text-sm px-3 py-1 bg-gray-700 hover:bg-gray-600 rounded">
              Clear
            </button>
          </div>
          <pre className="bg-black p-4 rounded h-64 overflow-auto text-sm text-green-400 font-mono">
            {response || "No logs yet..."}
          </pre>
        </div>
      </div>
    </main>
  );
}
