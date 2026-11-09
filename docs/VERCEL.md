# Vercel 웹 배포

## 구성

- Vite + Chart.js 정적 웹 화면 (`web/`)
- Node.js 22 서버리스 함수 (`api/indicators.js`)
- 공식 World Bank WDI / FRED 공개 CSV 조회. API 키 불필요.
- 원래 Streamlit·SQLite 프로그램은 로컬 분석 및 영구 이력용으로 유지.

Vercel의 함수 파일시스템은 영구 DB가 아닙니다. 웹 버전은 조회·비교·CSV/HTML 다운로드를 제공하며 영구 저장 기능을 주장하지 않습니다. 전체 보고서·개정 이력 관리에는 Python 프로그램 또는 별도 영속 DB가 필요합니다.

## GitHub에서 가져오기

https://vercel.com/new/import?s=https%3A%2F%2Fgithub.com%2FKo-young-jun%2FAnalysis_Company

1. Vercel에 GitHub 계정으로 로그인합니다.
2. `Ko-young-jun/Analysis_Company` 저장소 접근을 허용합니다.
3. 루트 디렉터리는 기본값을 사용합니다. Framework는 Vite, Build는 `npm run build`, Output은 `dist`입니다. `vercel.json`에 설정돼 있습니다.
4. 첫 배포에는 환경변수가 필요하지 않습니다. Deploy를 실행하면 Vercel이 실제 접속 URL을 생성합니다.

이미 저장소가 Vercel 프로젝트에 연결되어 있다면 main 푸시가 자동 배포를 시작할 수 있습니다. 배포 성공 여부와 URL은 Vercel에서 실제 결과로 확인해야 합니다.

## 검증

```bash
npm ci
npm test
npm run build
```

`npm run dev`는 프런트엔드 개발 서버이며 `/api/indicators`를 실행하지 않습니다. 로컬 통합 실행에는 Vercel CLI의 `vercel dev`와 계정 연결이 필요합니다. API가 없거나 공급자가 실패하면 실제 수치를 생성하지 않고 오류 상태를 표시합니다.

프로덕션 확인:

- `/`: 한국어 대시보드
- `/api/indicators?id=wb:NY.GDP.MKTP.KD.ZG`: 공식 WDI JSON 응답
- 지표 변경, 국가 선택, CSV·HTML 다운로드, 모바일 레이아웃
- 공급자 실패 시 HTTP 503, 잘못된 지표는 400

공식 자료 조회는 Vercel 서버에서 이루어지므로 이 개발 환경의 네트워크 차단과는 별개입니다. 공급자의 접근 제한·지연이 있을 수 있으며, 실제 배포 후 검증해야 합니다. 응답은 최대 15분 CDN 캐시될 수 있고 원 조회시각을 표시합니다.
