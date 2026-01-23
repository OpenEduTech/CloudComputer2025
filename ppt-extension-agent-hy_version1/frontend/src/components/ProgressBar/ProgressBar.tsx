type ProgressBarProps = {
  status: string
  progress: number
}

function ProgressBar({ status, progress }: ProgressBarProps) {
  return (
    <div className="bg-white rounded-lg shadow p-6">
      <div className="space-y-3">
        <div className="flex items-center justify-between">
          <span className="text-sm font-medium text-gray-700">处理状态</span>
          <div className="flex items-center gap-2">
            <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-primary-600"></div>
            <span className="text-sm font-medium text-primary-600">{status || '处理中...'}</span>
          </div>
        </div>
        <div className="w-full bg-gray-200 rounded-full h-2.5 overflow-hidden">
          <div
            className="bg-primary-600 h-2.5 rounded-full transition-all duration-500 ease-out"
            style={{ width: `${progress}%` }}
          />
        </div>
        <div className="flex items-center justify-between text-xs text-gray-500">
          <span>{status || '处理中...'}</span>
          <span>{progress}%</span>
        </div>
      </div>
    </div>
  )
}

export default ProgressBar
