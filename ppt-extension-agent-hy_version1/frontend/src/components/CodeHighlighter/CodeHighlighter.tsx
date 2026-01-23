import React from 'react'
import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter'
import { vscDarkPlus } from 'react-syntax-highlighter/dist/esm/styles/prism'

type CodeHighlighterProps = {
  content: string
  language?: string
}

function CodeHighlighter({ content, language = 'python' }: CodeHighlighterProps) {
  const extractCodeBlocks = (text: string) => {
    const codeBlockRegex = /```(\w*)\n([\s\S]*?)```/g
    const parts: React.ReactNode[] = []
    let lastIndex = 0
    let match

    while ((match = codeBlockRegex.exec(text)) !== null) {
      const before = text.slice(lastIndex, match.index)
      if (before) {
        parts.push(
          <div key={`text-${lastIndex}`} className="mb-4 whitespace-pre-wrap">
            {before}
          </div>
        )
      }

      const codeLanguage = match[1] || language
      const codeContent = match[2]

      try {
        parts.push(
          <div key={`code-${match.index}`} className="mb-4">
            <SyntaxHighlighter
              language={codeLanguage}
              style={vscDarkPlus}
              showLineNumbers
              wrapLines
              customStyle={{
                borderRadius: '0.5rem',
                fontSize: '0.875rem',
              }}
            >
              {codeContent}
            </SyntaxHighlighter>
          </div>
        )
      } catch (error) {
        parts.push(
          <pre key={`code-error-${match.index}`} className="bg-gray-100 p-4 rounded-lg overflow-x-auto">
            <code>{codeContent}</code>
          </pre>
        )
      }

      lastIndex = match.index + match[0].length
    }

    const remaining = text.slice(lastIndex)
    if (remaining) {
      parts.push(
        <div key={`text-${lastIndex}`} className="whitespace-pre-wrap">
          {remaining}
        </div>
      )
    }

    return parts.length > 0 ? parts : text
  }

  return <div className="code-highlighter">{extractCodeBlocks(content)}</div>
}

export default CodeHighlighter
