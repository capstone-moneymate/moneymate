import { createBrowserRouter } from 'react-router'
import { AppLayout } from '@/components/AppLayout'
import { CardNewsPage } from '@/pages/tab1/CardNewsPage'
import { LearnPage } from '@/pages/tab1/LearnPage'
import { NewsHomePage } from '@/pages/tab1/NewsHomePage'
import { ResultPage } from '@/pages/tab1/ResultPage'
import { EtfPage } from '@/pages/tab2/EtfPage'
import { MyPage } from '@/pages/tab3/MyPage'

export const router = createBrowserRouter([
  {
    element: <AppLayout />,
    children: [
      { path: '/', element: <NewsHomePage /> },
      { path: '/news/:cardId', element: <CardNewsPage /> },
      { path: '/news/:cardId/learn', element: <LearnPage /> },
      { path: '/news/:cardId/result', element: <ResultPage /> },
      { path: '/etf', element: <EtfPage /> },
      { path: '/mypage', element: <MyPage /> },
    ],
  },
])
