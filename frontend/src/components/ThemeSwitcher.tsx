'use client'

import { useEffect, useState } from 'react'
import { Button } from '@/components/ui/Button'
import { Palette } from 'lucide-react'

export function ThemeSwitcher() {
  const [theme, setTheme] = useState('minimal')

  useEffect(() => {
    const saved = localStorage.getItem('theme') || 'minimal'
    setTheme(saved)
    document.documentElement.setAttribute('data-theme', saved)
  }, [])

  const toggleTheme = () => {
    const next = theme === 'minimal' ? 'neo-brutal' : 'minimal'
    setTheme(next)
    localStorage.setItem('theme', next)
    document.documentElement.setAttribute('data-theme', next)
  }

  return (
    <Button variant="ghost" size="sm" onClick={toggleTheme} title="Toggle Theme (Minimal / Neo-brutal)">
      <Palette className="mr-2 h-4 w-4" />
      {theme === 'minimal' ? 'Minimal' : 'Neo-brutal'}
    </Button>
  )
}
