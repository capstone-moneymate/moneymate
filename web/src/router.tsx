import { createBrowserRouter, redirect } from 'react-router'
import { AppLayout } from '@/components/AppLayout'
import { ENTRY_FREE_PATHS, hasEntered } from '@/lib/entry'
import { LoginPage } from '@/pages/auth/LoginPage'
import { WelcomePage } from '@/pages/auth/WelcomePage'
import { CardNewsPage } from '@/pages/tab1/CardNewsPage'
import { LearnPage } from '@/pages/tab1/LearnPage'
import { NewsHomePage } from '@/pages/tab1/NewsHomePage'
import { ResultPage } from '@/pages/tab1/ResultPage'
import { EtfPage } from '@/pages/tab2/EtfPage'
import { StockDetailPage } from '@/pages/tab2/StockDetailPage'
import { CausalMapPage } from '@/pages/tab3/CausalMapPage'
import { MyPage } from '@/pages/tab3/MyPage'

export const router = createBrowserRouter([
  {
    element: <AppLayout />,
    // 처음 여는 사람은 시작 화면(로그인하기 · 가입하기 · 둘러보기)부터 본다
    loader: ({ request }) => {
      const { pathname } = new URL(request.url)
      if (!ENTRY_FREE_PATHS.includes(pathname) && !hasEntered()) return redirect('/welcome')
      return null
    },
    children: [
      { path: '/welcome', element: <WelcomePage /> },
      { path: '/', element: <NewsHomePage /> },
      { path: '/news/:cardId', element: <CardNewsPage /> },
      { path: '/news/:cardId/learn', element: <LearnPage /> },
      { path: '/news/:cardId/result', element: <ResultPage /> },
      { path: '/etf', element: <EtfPage /> },
      { path: '/etf/:ticker', element: <StockDetailPage /> },
      { path: '/mypage', element: <MyPage /> },
      { path: '/mypage/map', element: <CausalMapPage /> },
      { path: '/login', element: <LoginPage /> },
    ],
  },
])
