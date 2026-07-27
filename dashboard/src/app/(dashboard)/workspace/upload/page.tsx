'use client'

import { useState } from 'react'
import { useRouter } from 'next/navigation'
import { useTranslations } from 'next-intl'
import { useWorkspace } from '../context'
import { DashboardLayout } from '@/components/dashboard-v2'
import { getUserId, getToken } from '@/lib/auth'
import { Upload, AlertCircle, FileText, CheckCircle, ArrowRight, Loader } from 'lucide-react'

export default function UploadPage() {
  const t = useTranslations('workspace')
  const router = useRouter()
  const { activeWorkspace } = useWorkspace()
  const [file, setFile] = useState<File | null>(null)
  const [title, setTitle] = useState('')
  const [uploading, setUploading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [success, setSuccess] = useState<boolean>(false)

  const handleDrag = (e: React.DragEvent) => {
    e.preventDefault()
    e.stopPropagation()
  }

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault()
    e.stopPropagation()
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      const selectedFile = e.dataTransfer.files[0]
      setFile(selectedFile)
      if (!title) setTitle(selectedFile.name.split('.')[0])
    }
  }

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      const selectedFile = e.target.files[0]
      setFile(selectedFile)
      if (!title) setTitle(selectedFile.name.split('.')[0])
    }
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!file || !activeWorkspace) return

    setUploading(true)
    setError(null)
    setSuccess(false)

    const ownerId = getUserId() || 'system'
    const formData = new FormData()
    formData.append('file', file)

    // Build URL query params since upload uses Query params for workspace/owner/title
    const queryParams = new URLSearchParams({
      workspace_id: activeWorkspace.id,
      owner_id: ownerId,
      title: title || file.name,
    })

    try {
      const token = getToken()
      const headers: Record<string, string> = {}
      if (token) {
        headers['Authorization'] = `Bearer ${token}`
      }

      const res = await fetch(`/api/v1/knowledge/upload?${queryParams.toString()}`, {
        method: 'POST',
        headers,
        body: formData,
      })

      if (!res.ok) {
        const text = await res.text()
        try {
          const json = JSON.parse(text)
          throw new Error(json.detail || json.error || `HTTP ${res.status}`)
        } catch {
          throw new Error(text || `HTTP ${res.status}`)
        }
      }

      setSuccess(true)
      setFile(null)
      setTitle('')
      
      // Redirect to processing queue after 1.5 seconds
      setTimeout(() => {
        router.push('/workspace/processing')
      }, 1500)
    } catch (err: any) {
      setError(err.message || t('upload_error'))
    } finally {
      setUploading(false)
    }
  }

  return (
    <DashboardLayout breadcrumbs={[{ label: t('crumb_workspace'), href: '/workspace' }, { label: t('crumb_upload') }]}>
      <div className="flex flex-col gap-6 max-w-2xl mx-auto">
        {/* Header */}
        <div>
          <h1 className="verge-display text-4xl text-v2-text-primary leading-none">{t('upload_title')}</h1>
          <p className="text-sm text-v2-text-secondary mt-1">
            {t('upload_subtitle')}
          </p>
        </div>

        {/* Status Alerts */}
        {error && (
          <div className="flex items-center gap-3 p-4 rounded-xl bg-v2-error/10 border border-v2-error/30 text-v2-error text-sm">
            <AlertCircle className="w-5 h-5 shrink-0" />
            <div className="flex-1">{error}</div>
          </div>
        )}

        {success && (
          <div className="flex items-center gap-3 p-4 rounded-xl bg-v2-success/10 border border-v2-success/30 text-v2-success text-sm">
            <CheckCircle className="w-5 h-5 shrink-0" />
            <div className="flex-1">{t('upload_success')}</div>
          </div>
        )}

        {/* Upload Form */}
        <form onSubmit={handleSubmit} className="flex flex-col gap-5">
          {/* File Drag Box */}
          <div
            onDragEnter={handleDrag}
            onDragOver={handleDrag}
            onDragLeave={handleDrag}
            onDrop={handleDrop}
            className={`border-2 border-dashed rounded-[20px] p-10 flex flex-col items-center justify-center gap-4 transition-colors relative bg-v2-surface/40 ${
              file ? 'border-v2-accent' : 'border-v2-border hover:border-v2-accent/60'
            }`}
          >
            <input
              type="file"
              onChange={handleFileChange}
              accept=".pdf,.txt,.md"
              className="absolute inset-0 opacity-0 cursor-pointer"
              disabled={uploading || success}
            />
            <div className={`p-4 rounded-full ${file ? 'bg-v2-accent-muted text-v2-accent' : 'bg-v2-bg text-v2-text-secondary'}`}>
              <Upload className="w-8 h-8" />
            </div>
            {file ? (
              <div className="text-center min-w-0 px-4">
                <p className="text-sm font-semibold text-v2-text-primary truncate">{file.name}</p>
                <p className="text-xs text-v2-text-secondary mt-1">
                  {t('file_selected_hint', { size: (file.size / 1024 / 1024).toFixed(2) })}
                </p>
              </div>
            ) : (
              <div className="text-center">
                <p className="text-sm font-semibold text-v2-text-primary">{t('dropzone_title')}</p>
                <p className="text-xs text-v2-text-secondary mt-1">
                  {t('dropzone_hint')}
                </p>
              </div>
            )}
          </div>

          {/* Title Input */}
          <div className="flex flex-col gap-2">
            <label className="text-xs text-v2-text-secondary uppercase tracking-wider font-semibold">{t('field_asset_title')}</label>
            <input
              type="text"
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              placeholder={t('asset_title_placeholder')}
              required
              disabled={uploading || success || !file}
              className="bg-v2-surface border border-v2-border text-v2-text-primary text-sm rounded-xl px-4 py-3 outline-none focus:border-v2-accent disabled:opacity-50"
            />
          </div>

          {/* Submit Button */}
          <button
            type="submit"
            disabled={uploading || success || !file}
            className="w-full h-12 rounded-xl bg-v2-accent text-v2-inverted text-sm font-bold hover:bg-white transition-all flex items-center justify-center gap-2 disabled:opacity-50 disabled:hover:bg-v2-accent"
          >
            {uploading ? (
              <>
                <Loader className="w-5 h-5 animate-spin" /> {t('ingesting')}
              </>
            ) : (
              <>
                {t('submit_ingestion')} <ArrowRight className="w-4 h-4" />
              </>
            )}
          </button>
        </form>
      </div>
    </DashboardLayout>
  )
}
