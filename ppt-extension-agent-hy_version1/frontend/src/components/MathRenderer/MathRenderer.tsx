import React from 'react'
import { InlineMath, BlockMath } from 'react-katex'
import 'katex/dist/katex.min.css'

type MathRendererProps = {
  content: string
  display?: boolean
}

function MathRenderer({ content, display = false }: MathRendererProps) {
  const renderMath = (text: string) => {
    const mathRegex = /\$\$([^$]+)\$\$|\$([^$]+)\$/g
    const parts: React.ReactNode[] = []
    let lastIndex = 0
    let match

    while ((match = mathRegex.exec(text)) !== null) {
      const before = text.slice(lastIndex, match.index)
      if (before) {
        parts.push(<span key={`text-${lastIndex}`}>{before}</span>)
      }

      const mathContent = match[1] || match[2]
      const isBlock = !!match[1]

      try {
        if (isBlock) {
          parts.push(
            <div key={`math-${match.index}`} className="my-4">
              <BlockMath math={mathContent} />
            </div>
          )
        } else {
          parts.push(
            <span key={`math-${match.index}`}>
              <InlineMath math={mathContent} />
            </span>
          )
        }
      } catch (error) {
        parts.push(
          <span key={`math-error-${match.index}`} className="text-red-500">
            {match[0]}
          </span>
        )
      }

      lastIndex = match.index + match[0].length
    }

    const remaining = text.slice(lastIndex)
    if (remaining) {
      parts.push(<span key={`text-${lastIndex}`}>{remaining}</span>)
    }

    return parts.length > 0 ? parts : text
  }

  return <div className="math-renderer">{renderMath(content)}</div>
}

export default MathRenderer
