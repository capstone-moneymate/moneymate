import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import '@/styles/index.css'
import { App } from '@/App'
import { getUserId } from '@/lib/userId'

// 첫 실행 때 익명 ID를 만들어 둔다
getUserId()

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <App />
  </StrictMode>,
)
