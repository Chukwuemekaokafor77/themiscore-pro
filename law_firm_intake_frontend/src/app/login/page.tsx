'use client'

import { useState } from 'react'
import { useForm } from 'react-hook-form'
import { z } from 'zod'
import { zodResolver } from '@hookform/resolvers/zod'

const TeamSchema = z.object({
  username: z.string().min(1),
  password: z.string().min(1),
})

const PortalSchema = z.object({
  email: z.string().email(),
  password: z.string().min(4),
})

type TeamValues = z.infer<typeof TeamSchema>
type PortalValues = z.infer<typeof PortalSchema>

export default function LoginPage() {
  const [tab, setTab] = useState<'team'|'portal'>('team')

  // Team Console form
  const { register: regTeam, handleSubmit: submitTeam, formState: { errors: teamErrors } } = useForm<TeamValues>({ resolver: zodResolver(TeamSchema) })
  const [teamSubmitting, setTeamSubmitting] = useState(false)
  const [teamError, setTeamError] = useState<string | null>(null)

  const onTeamSubmit = async (values: TeamValues) => {
    setTeamSubmitting(true)
    setTeamError(null)
    try {
      const res = await fetch('/api/auth/team', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(values)
      })
      if (!res.ok) {
        setTeamError('Invalid credentials')
        return
      }
      window.location.href = '/dashboard'
    } catch (e) {
      setTeamError('Sign-in failed')
    } finally {
      setTeamSubmitting(false)
    }
  }

  // Client Portal form
  const { register: regPortal, handleSubmit: submitPortal, formState: { errors: portalErrors } } = useForm<PortalValues>({ resolver: zodResolver(PortalSchema) })
  const [portalSubmitting, setPortalSubmitting] = useState(false)
  const [portalError, setPortalError] = useState<string | null>(null)

  const onPortalSubmit = async (values: PortalValues) => {
    setPortalSubmitting(true)
    setPortalError(null)
    try {
      const res = await fetch('/api/portal/login', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(values)
      })
      if (!res.ok) {
        setPortalError('Invalid email or password')
        return
      }
      window.location.href = '/portal'
    } catch (e) {
      setPortalError('Sign-in failed')
    } finally {
      setPortalSubmitting(false)
    }
  }

  return (
    <div className="max-w-md mx-auto p-6">
      <h1 className="text-2xl font-semibold mb-4">Sign in</h1>
      <div className="flex gap-4 border-b mb-4">
        <button className={`py-2 ${tab==='team' ? 'border-b-2 border-black font-medium' : 'text-gray-600'}`} onClick={() => setTab('team')}>Team Console</button>
        <button className={`py-2 ${tab==='portal' ? 'border-b-2 border-black font-medium' : 'text-gray-600'}`} onClick={() => setTab('portal')}>Client Portal</button>
      </div>

      {tab === 'team' && (
        <form onSubmit={submitTeam(onTeamSubmit)} className="space-y-4">
          <div>
            <label className="block text-sm font-medium mb-1">Username</label>
            <input type="text" className="w-full border rounded px-3 py-2" placeholder="your.username" {...regTeam('username')} />
            {teamErrors.username && <p className="text-red-600 text-sm mt-1">{teamErrors.username.message}</p>}
          </div>
          <div>
            <label className="block text-sm font-medium mb-1">Password</label>
            <input type="password" className="w-full border rounded px-3 py-2" placeholder="••••••••" {...regTeam('password')} />
            {teamErrors.password && <p className="text-red-600 text-sm mt-1">{teamErrors.password.message}</p>}
          </div>
          {teamError && <div className="text-red-700 text-sm">{teamError}</div>}
          <button type="submit" disabled={teamSubmitting} className="w-full px-4 py-2 bg-black text-white rounded disabled:opacity-50">
            {teamSubmitting ? 'Signing in…' : 'Sign in'}
          </button>
        </form>
      )}

      {tab === 'portal' && (
        <form onSubmit={submitPortal(onPortalSubmit)} className="space-y-4">
          <div>
            <label className="block text-sm font-medium mb-1">Email</label>
            <input type="email" className="w-full border rounded px-3 py-2" placeholder="you@example.com" {...regPortal('email')} />
            {portalErrors.email && <p className="text-red-600 text-sm mt-1">{portalErrors.email.message}</p>}
          </div>
          <div>
            <label className="block text-sm font-medium mb-1">Password</label>
            <input type="password" className="w-full border rounded px-3 py-2" placeholder="••••••••" {...regPortal('password')} />
            {portalErrors.password && <p className="text-red-600 text-sm mt-1">{portalErrors.password.message}</p>}
          </div>
          {portalError && <div className="text-red-700 text-sm">{portalError}</div>}
          <div className="flex items-center justify-between">
            <span className="text-sm text-gray-600">Forgot password?</span>
          </div>
          <button type="submit" disabled={portalSubmitting} className="w-full px-4 py-2 bg-black text-white rounded disabled:opacity-50">
            {portalSubmitting ? 'Signing in…' : 'Sign in'}
          </button>
        </form>
      )}
    </div>
  )
}
