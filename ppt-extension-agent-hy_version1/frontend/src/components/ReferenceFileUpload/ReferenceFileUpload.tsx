import { useState, useRef } from 'react'
import { FileText, X, Upload as UploadIcon } from 'lucide-react'

type ReferenceFile = {
  file_id: string
  filename: string
  file_type: string
  word_count: number
}

type ReferenceFileUploadProps = {
  onFilesChange: (fileIds: string[]) => void
}

function ReferenceFileUpload({ onFilesChange }: ReferenceFileUploadProps) {
  const [referenceFiles, setReferenceFiles] = useState<ReferenceFile[]>([])
  const [isDragging, setIsDragging] = useState(false)
  const [isUploading, setIsUploading] = useState(false)
  const fileInputRef = useRef<HTMLInputElement>(null)

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault()
    setIsDragging(true)
  }

  const handleDragLeave = (e: React.DragEvent) => {
    e.preventDefault()
    setIsDragging(false)
  }

  const handleDrop = async (e: React.DragEvent) => {
    e.preventDefault()
    setIsDragging(false)

    const files = Array.from(e.dataTransfer.files)
    const validFiles = files.filter((f) =>
      f.name.endsWith('.docx') || f.name.endsWith('.doc') || f.name.endsWith('.pdf')
    )

    if (validFiles.length > 0) {
      await uploadFiles(validFiles)
    }
  }

  const handleFileSelect = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = e.target.files
    if (files && files.length > 0) {
      await uploadFiles(Array.from(files))
    }
  }

  const uploadFiles = async (files: File[]) => {
    setIsUploading(true)

    try {
      const uploadPromises = files.map(async (file) => {
        const formData = new FormData()
        formData.append('file', file)

        const response = await fetch('/api/v1/upload-reference', {
          method: 'POST',
          body: formData,
        })

        if (!response.ok) {
          throw new Error(`上传失败: ${file.name}`)
        }

        return response.json()
      })

      const results = await Promise.all(uploadPromises)
      const newFiles = results.map((r) => ({
        file_id: r.file_id,
        filename: r.filename,
        file_type: r.file_type,
        word_count: r.word_count,
      }))

      const updatedFiles = [...referenceFiles, ...newFiles]
      setReferenceFiles(updatedFiles)
      onFilesChange(updatedFiles.map((f) => f.file_id))
    } catch (error) {
      console.error('Upload failed:', error)
      alert('上传失败，请重试')
    } finally {
      setIsUploading(false)
    }
  }

  const handleRemoveFile = async (fileId: string) => {
    try {
      const response = await fetch(`/api/v1/reference/${fileId}`, {
        method: 'DELETE',
      })

      if (!response.ok) {
        throw new Error('删除失败')
      }

      const updatedFiles = referenceFiles.filter((f) => f.file_id !== fileId)
      setReferenceFiles(updatedFiles)
      onFilesChange(updatedFiles.map((f) => f.file_id))
    } catch (error) {
      console.error('Delete failed:', error)
      alert('删除失败，请重试')
    }
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h3 className="text-lg font-semibold text-gray-900">参考文件（可选）</h3>
        <span className="text-sm text-gray-500">
          上传Word或PDF文件作为扩充依据
        </span>
      </div>

      <div
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
        onDrop={handleDrop}
        onClick={() => fileInputRef.current?.click()}
        className={`border-2 border-dashed rounded-lg p-6 text-center cursor-pointer transition-colors ${
          isDragging
            ? 'border-primary-500 bg-primary-50'
            : 'border-gray-300 hover:border-primary-400 hover:bg-gray-50'
        }`}
      >
        <input
          ref={fileInputRef}
          type="file"
          accept=".docx,.doc,.pdf"
          multiple
          onChange={handleFileSelect}
          className="hidden"
        />
        <UploadIcon className="w-8 h-8 mx-auto mb-2 text-gray-400" />
        <p className="text-sm text-gray-700 mb-1">
          拖拽文件到此处，或点击选择文件
        </p>
        <p className="text-xs text-gray-500">
          支持 .docx、.doc、.pdf 格式
        </p>
      </div>

      {isUploading && (
        <div className="text-center py-2">
          <div className="inline-block animate-spin rounded-full h-5 w-5 border-b-2 border-primary-600"></div>
          <p className="mt-1 text-xs text-gray-600">正在上传...</p>
        </div>
      )}

      {referenceFiles.length > 0 && (
        <div className="space-y-2">
          <p className="text-sm font-medium text-gray-700">已上传的参考文件：</p>
          {referenceFiles.map((file) => (
            <div
              key={file.file_id}
              className="flex items-center justify-between p-3 bg-gray-50 rounded-lg border border-gray-200"
            >
              <div className="flex items-center gap-3 flex-1 min-w-0">
                <FileText className="w-5 h-5 text-gray-500 flex-shrink-0" />
                <div className="flex-1 min-w-0">
                  <p className="text-sm font-medium text-gray-900 truncate">
                    {file.filename}
                  </p>
                  <p className="text-xs text-gray-500">
                    {file.file_type.toUpperCase()} · {file.word_count.toLocaleString()} 字
                  </p>
                </div>
              </div>
              <button
                onClick={(e) => {
                  e.stopPropagation()
                  handleRemoveFile(file.file_id)
                }}
                className="p-1 text-gray-400 hover:text-red-600 transition-colors flex-shrink-0"
                title="删除"
              >
                <X className="w-4 h-4" />
              </button>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}

export default ReferenceFileUpload
