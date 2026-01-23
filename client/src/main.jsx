/**
 * PatPat-Inconsistency-Hunter 前端入口
 * 长文本事实卫士 - React应用主入口
 */

import React from 'react'
import ReactDOM from 'react-dom/client'
import App from './App'
import './index.css'

ReactDOM.createRoot(document.getElementById('root')).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>,
)

