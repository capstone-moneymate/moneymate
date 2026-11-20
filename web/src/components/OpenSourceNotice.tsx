/**
 * 오픈소스 라이선스 안내 (마이페이지 맨 아래).
 * 차트 라이브러리 lightweight-charts(Apache-2.0)는 사용자가 볼 수 있는 화면 한 곳에 TradingView 출처 표기와
 * 링크를 요구한다. 차트마다 붙이지 않고 여기 한 곳에 모았다 (차트 쪽은 attributionLogo: false).
 */
export const OpenSourceNotice = () => (
  <details className="mt-8 rounded-2xl bg-slate-50 px-4 py-3 text-xs text-slate-500">
    <summary className="flex min-h-9 cursor-pointer items-center font-semibold text-slate-600">
      오픈소스 라이선스
    </summary>
    <p className="mt-2 leading-relaxed">
      차트는{' '}
      <a
        href="https://www.tradingview.com/"
        target="_blank"
        rel="noreferrer"
        className="text-slate-700 underline"
      >
        TradingView
      </a>
      의 TradingView Lightweight Charts™ 로 그립니다.
      <br />
      Copyright 2023 TradingView, Inc. · Apache License 2.0
    </p>
  </details>
)
