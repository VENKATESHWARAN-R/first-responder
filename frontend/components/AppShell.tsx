'use client';

import { usePathname } from 'next/navigation';
import { Nav } from './Nav';

export function AppShell({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const hideNav = pathname === '/login';

  return (
    <>
      {!hideNav && (
        <div className="container" style={{ paddingBottom: 0 }}>
          <Nav />
        </div>
      )}
      {children}
    </>
  );
}
