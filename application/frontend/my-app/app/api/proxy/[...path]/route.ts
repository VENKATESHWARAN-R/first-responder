import { NextRequest, NextResponse } from 'next/server';

export async function GET(
  request: NextRequest,
  { params }: { params: Promise<{ path: string[] }> }
) {
  const resolvedParams = await params;
  return proxyToBackend(request, resolvedParams.path, 'GET');
}

export async function POST(
  request: NextRequest,
  { params }: { params: Promise<{ path: string[] }> }
) {
  const resolvedParams = await params;
  return proxyToBackend(request, resolvedParams.path, 'POST');
}

async function proxyToBackend(
  request: NextRequest,
  pathSegments: string[],
  method: string
) {
  const backendUrl = process.env.BACKEND_URL || 'http://localhost:8000';
  
  // Reconstruct the path
  const path = pathSegments ? `/${pathSegments.join('/')}`  : '/';
  
  // Get query parameters
  const searchParams = request.nextUrl.searchParams;
  const queryString = searchParams.toString();
  const fullPath = queryString ? `${path}?${queryString}` : path;
  
  const targetUrl = `${backendUrl}${fullPath}`;
  
  console.log(`[Proxy] ${method} ${targetUrl}`);
  
  try {
    const options: RequestInit = {
      method,
      headers: {
        'Content-Type': 'application/json',
      },
    };
    
    // Add body for POST requests
    if (method === 'POST') {
      const body = await request.json();
      options.body = JSON.stringify(body);
    }
    
    const response = await fetch(targetUrl, options);
    const data = await response.json();
    
    return NextResponse.json(data, { status: response.status });
  } catch (error) {
    console.error('[Proxy] Error:', error);
    return NextResponse.json(
      { 
        error: 'Backend connection failed',
        details: String(error),
        targetUrl 
      },
      { status: 500 }
    );
  }
}
