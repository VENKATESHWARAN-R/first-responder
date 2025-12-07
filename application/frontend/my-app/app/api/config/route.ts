import { NextResponse } from 'next/server';

export async function GET() {
  // Read backend URL from environment variable
  // This runs server-side, so it can access runtime environment variables
  const backendUrl = process.env.BACKEND_URL || 'http://localhost:8000';
  
  return NextResponse.json({
    backendUrl,
  });
}
