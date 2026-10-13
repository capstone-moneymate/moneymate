import { createBrowserRouter } from 'react-router'
import { AppLayout } from '@/components/AppLayout'
import { CardNewsPage } from '@/pages/tab1/CardNewsPage'
import { NewsHomePage } from '@/pages/tab1/NewsHomePage'
import { EtfPage } from '@/pages/tab2/EtfPage'
import { MyPage } from '@/pages/tab3/MyPage'

export const router = createBrowserRouter([
  {
    element: <AppLayout />,
    children: [
      { path: '/', element: <NewsHomePage /> },
      { path: '/news/:cardId', element: <CardNewsPage /> },
      { path: '/etf', element: <EtfPage /> },
      { path: '/mypage', element: <MyPage /> },
    ],
  },
])
