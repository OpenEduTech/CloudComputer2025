import { useState } from 'react'
import { ChevronLeft, ChevronRight, ChevronDown, ChevronUp } from 'lucide-react'

type Slide = {
  page_number: number
  title: string
  text_boxes: Array<{
    id: number
    text: string
    position: { left: number; top: number; width: number; height: number }
    is_title: boolean
  }>
  images?: Array<{
    id: number
    file_path: string
    position: { left: number; top: number; width: number; height: number }
    description?: string
    ocr_text?: string
  }>
}

type PPTViewerProps = {
  slides: Slide[]
  currentSlide: number
  onSlideChange: (index: number) => void
  selectedTextBoxes: number[]
  onTextBoxSelect: (id: number) => void
  selectedImages: number[]
  onImageSelect: (id: number) => void
}

function PPTViewer({
  slides,
  currentSlide,
  onSlideChange,
  selectedTextBoxes,
  onTextBoxSelect,
  selectedImages,
  onImageSelect,
}: PPTViewerProps) {
  const slide = slides[currentSlide]

  if (!slide) return null

  // 过滤出有有效文字内容的图片
  // 完全排除描述为"图片中未识别到文字内容"的图片
  const imagesWithText = slide.images?.filter((img) => {
    // 如果描述是"图片中未识别到文字内容"，直接排除
    if (img.description === '图片中未识别到文字内容') {
      return false
    }
    // 检查是否有有效的描述或OCR文字
    const hasValidDescription = img.description && 
      img.description.trim() !== '' && 
      img.description !== '图片中未识别到文字内容'
    const hasOcrText = img.ocr_text && img.ocr_text.trim() !== ''
    return hasValidDescription || hasOcrText
  }) || []

  // 管理每个图片的OCR文字展开状态
  const [expandedOcrTexts, setExpandedOcrTexts] = useState<Set<number>>(new Set())

  const toggleOcrText = (imageId: number) => {
    setExpandedOcrTexts((prev) => {
      const newSet = new Set(prev)
      if (newSet.has(imageId)) {
        newSet.delete(imageId)
      } else {
        newSet.add(imageId)
      }
      return newSet
    })
  }

  return (
    <div className="space-y-4">
      <div className="bg-gradient-to-br from-blue-50 to-indigo-50 rounded-lg p-8 min-h-[400px] relative">
        <h3 className="text-2xl font-bold text-gray-900 mb-6">
          {slide.title || `第 ${slide.page_number} 页`}
        </h3>

        {slide.text_boxes.length === 0 && imagesWithText.length === 0 ? (
          <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-4 text-center">
            <p className="text-sm text-yellow-800">
              本页暂无可选中内容。请尝试选择其他页面，或使用"扩展整页"功能。
            </p>
          </div>
        ) : (
          <>
            {slide.text_boxes.length > 0 && (
              <div className="space-y-3">
                {slide.text_boxes.map((textBox) => (
                  <div
                    key={textBox.id}
                    onClick={() => onTextBoxSelect(textBox.id)}
                    className={`p-3 rounded-lg cursor-pointer transition-all ${
                      selectedTextBoxes.includes(textBox.id)
                        ? 'bg-primary-100 border-2 border-primary-500 shadow-md'
                        : 'bg-white border border-gray-200 hover:border-primary-300 hover:shadow-sm'
                    }`}
                  >
                    <p
                      className={`text-sm ${
                        textBox.is_title
                          ? 'font-semibold text-gray-900'
                          : 'text-gray-700'
                      }`}
                    >
                      {textBox.text}
                    </p>
                  </div>
                ))}
              </div>
            )}

            {/* 显示有文字的图片，并支持选择 */}
            {imagesWithText.length > 0 && (
              <div className="mt-6 space-y-4">
                <h4 className="text-lg font-semibold text-gray-900">图片内容</h4>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  {imagesWithText.map((image) => (
                    <div
                      key={image.id}
                      onClick={() => onImageSelect(image.id)}
                      className={`bg-white rounded-lg border p-4 shadow-sm cursor-pointer transition-all ${
                        selectedImages.includes(image.id)
                          ? 'border-2 border-primary-500 bg-primary-50 shadow-md'
                          : 'border-gray-200 hover:border-primary-300 hover:shadow-md'
                      }`}
                    >
                      {image.file_path && (
                        <div className="mb-3">
                          <img
                            src={`http://localhost:8000/uploads/${image.file_path}`}
                            alt={`Slide ${slide.page_number} Image ${image.id}`}
                            className="w-full h-auto rounded-lg border border-gray-200"
                            onError={(e) => {
                              console.error('Image load error:', image.file_path)
                              e.currentTarget.style.display = 'none'
                            }}
                          />
                        </div>
                      )}
                      {image.description && image.description !== '图片中未识别到文字内容' && (
                        <p className="text-sm text-gray-700 mb-2">
                          <span className="font-semibold">描述：</span>
                          {image.description}
                        </p>
                      )}
                      {image.ocr_text && 
                       image.ocr_text.trim() !== '' && 
                       image.ocr_text !== image.description && (
                        <div className="mt-2">
                          <button
                            onClick={(e) => {
                              e.stopPropagation() // 阻止触发图片选择
                              toggleOcrText(image.id)
                            }}
                            className="flex items-center gap-1 text-sm text-gray-600 hover:text-gray-900 transition-colors"
                          >
                            <span className="font-semibold">识别文字：</span>
                            {expandedOcrTexts.has(image.id) ? (
                              <>
                                <ChevronUp className="w-4 h-4" />
                                <span className="text-xs">收起</span>
                              </>
                            ) : (
                              <>
                                <ChevronDown className="w-4 h-4" />
                                <span className="text-xs">展开</span>
                              </>
                            )}
                          </button>
                          {expandedOcrTexts.has(image.id) && (
                            <p className="text-sm text-gray-600 mt-2 p-2 bg-gray-50 rounded border border-gray-200">
                              {image.ocr_text}
                            </p>
                          )}
                        </div>
                      )}
                      {selectedImages.includes(image.id) && (
                        <div className="mt-2 text-xs text-primary-600 font-semibold">
                          ✓ 已选中
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              </div>
            )}
          </>
        )}
      </div>

      <div className="flex items-center justify-between">
        <button
          onClick={() => onSlideChange(Math.max(0, currentSlide - 1))}
          disabled={currentSlide === 0}
          className="flex items-center gap-2 px-4 py-2 bg-white border border-gray-300 rounded-lg hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
        >
          <ChevronLeft className="w-4 h-4" />
          上一页
        </button>

        <div className="text-sm text-gray-600">
          {currentSlide + 1} / {slides.length}
        </div>

        <button
          onClick={() => onSlideChange(Math.min(slides.length - 1, currentSlide + 1))}
          disabled={currentSlide === slides.length - 1}
          className="flex items-center gap-2 px-4 py-2 bg-white border border-gray-300 rounded-lg hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
        >
          下一页
          <ChevronRight className="w-4 h-4" />
        </button>
      </div>
    </div>
  )
}

export default PPTViewer
