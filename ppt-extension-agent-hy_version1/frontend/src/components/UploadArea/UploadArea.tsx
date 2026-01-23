import { useState, useRef } from 'react'
import { Upload as UploadIcon, Link as LinkIcon } from 'lucide-react'

type PPTData = {
  metadata: {
    file_name: string
    slide_count: number
  }
  slides: any[]
}

type UploadAreaProps = {
  onUpload: (data: PPTData) => void
}

function UploadArea({ onUpload }: UploadAreaProps) {
  const [isDragging, setIsDragging] = useState(false)
  const [url, setUrl] = useState('')
  const [isLoading, setIsLoading] = useState(false)
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
    const pptFile = files.find((f) =>
      f.name.endsWith('.pptx') || f.name.endsWith('.ppt')
    )

    if (pptFile) {
      await uploadFile(pptFile)
    }
  }

  const handleFileSelect = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = e.target.files
    if (files && files[0]) {
      await uploadFile(files[0])
    }
  }

  const uploadFile = async (file: File) => {
    setIsLoading(true)
    const formData = new FormData()
    formData.append('file', file)

    try {
      const response = await fetch('/api/v1/upload', {
        method: 'POST',
        body: formData,
      })

      if (!response.ok) {
        throw new Error('上传失败')
      }

      const data = await response.json()
      console.log('=== API返回的完整数据 ===', data)
      console.log('=== ppt_data ===', data.ppt_data)
      if (data.ppt_data && data.ppt_data.slides && data.ppt_data.slides.length > 0) {
        console.log('=== 第1页数据 ===', data.ppt_data.slides[0])
        console.log('=== 第1页图片数量 ===', data.ppt_data.slides[0].images?.length || 0)
        if (data.ppt_data.slides[0].images && data.ppt_data.slides[0].images.length > 0) {
          console.log('=== 第1个图片 ===', data.ppt_data.slides[0].images[0])
        }
      }
      onUpload(data.ppt_data)
    } catch (error) {
      console.error('Upload failed:', error)
      alert('上传失败，请重试')
    } finally {
      setIsLoading(false)
    }
  }

  const handleURLSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!url) return

    setIsLoading(true)

    try {
      const response = await fetch('/api/v1/process-url', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ url }),
      })

      if (!response.ok) {
        throw new Error('处理失败')
      }

      const data = await response.json()
      onUpload(data.ppt_data)
    } catch (error) {
      console.error('URL processing failed:', error)
      alert('处理失败，请重试')
    } finally {
      setIsLoading(false)
    }
  }

  return (
    <div className="max-w-2xl mx-auto">
      <div className="bg-white rounded-lg shadow-lg p-8">
        <h2 className="text-2xl font-bold text-gray-900 mb-6 text-center">
          上传PPT文件
        </h2>

        <div
          onDragOver={handleDragOver}
          onDragLeave={handleDragLeave}
          onDrop={handleDrop}
          onClick={() => fileInputRef.current?.click()}
          className={`border-2 border-dashed rounded-lg p-12 text-center cursor-pointer transition-colors ${
            isDragging
              ? 'border-primary-500 bg-primary-50'
              : 'border-gray-300 hover:border-primary-400 hover:bg-gray-50'
          }`}
        >
          <input
            ref={fileInputRef}
            type="file"
            accept=".pptx,.ppt"
            onChange={handleFileSelect}
            className="hidden"
          />
          <UploadIcon className="w-16 h-16 mx-auto mb-4 text-gray-400" />
          <p className="text-lg text-gray-700 mb-2">
            拖拽PPT文件到此处，或点击选择文件
          </p>
          <p className="text-sm text-gray-500">
            支持 .pptx 和 .ppt 格式
          </p>
        </div>

        <div className="mt-8">
          <div className="relative">
            <div className="absolute inset-0 flex items-center">
              <div className="w-full border-t border-gray-300" />
            </div>
            <div className="relative flex justify-center text-sm">
              <span className="px-2 bg-white text-gray-500">或</span>
            </div>
          </div>
        </div>

        <form onSubmit={handleURLSubmit} className="mt-6">
          <div className="flex gap-3">
            <div className="flex-1 relative">
              <LinkIcon className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-gray-400" />
              <input
                type="url"
                value={url}
                onChange={(e) => setUrl(e.target.value)}
                placeholder="输入PPT文件的URL地址"
                className="w-full pl-10 pr-4 py-2.5 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-transparent outline-none"
                disabled={isLoading}
              />
            </div>
            <button
              type="submit"
              disabled={isLoading || !url}
              className="px-6 py-2.5 bg-primary-600 text-white rounded-lg hover:bg-primary-700 disabled:bg-gray-300 disabled:cursor-not-allowed transition-colors font-medium"
            >
              {isLoading ? '处理中...' : '处理URL'}
            </button>
          </div>
        </form>

        {isLoading && (
          <div className="mt-6 text-center">
            <div className="inline-block animate-spin rounded-full h-8 w-8 border-b-2 border-primary-600"></div>
            <p className="mt-2 text-sm text-gray-600">正在处理...</p>
          </div>
        )}
      </div>
    </div>
  )
}

export default UploadArea