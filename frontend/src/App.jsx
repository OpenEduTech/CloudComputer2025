import { useState, useEffect } from 'react'
import axios from 'axios'

function App() {
  const [status, setStatus] = useState('Checking Backend...')
  const [redisStatus, setRedisStatus] = useState('Unknown')

  useEffect(() => {
    // 检查后端健康状态
    axios.get('/api/')
      .then(res => {
        setStatus(res.data.status)
        setRedisStatus(res.data.redis_connection)
      })
      .catch(err => {
        setStatus('Backend Offline')
        console.error(err)
      })
  }, [])

  return (
    <div style={{ padding: '2rem', fontFamily: 'Arial, sans-serif' }}>
      <h1>AutoKGS Platform</h1>
      <div style={{ padding: '1rem', border: '1px solid #ccc', borderRadius: '8px', maxWidth: '400px' }}>
        <h2>System Status</h2>
        <p><strong>Frontend:</strong> <span style={{ color: 'green' }}>Running</span></p>
        <p><strong>Backend:</strong> <span style={{ color: status === 'running' ? 'green' : 'red' }}>{status}</span></p>
        <p><strong>Redis:</strong> <span style={{ color: redisStatus.includes('connected') ? 'green' : 'orange' }}>{redisStatus}</span></p>
      </div>
      <p style={{ marginTop: '20px', color: '#666' }}>
        If you see green lights above, your infrastructure is ready!
      </p>
    </div>
  )
}

export default App
