> 초안 (Claude 작성, 2026-11-20). 담당자 C가 읽고 고쳐서 확정한다.

# 배포 (AWS EC2 + Docker Compose)

**한 줄 설명**: EC2 한 대에서 `docker-compose.yml` + `docker-compose.prod.yml` 로 db·judge·server·web·scheduler 5개 컨테이너를 띄운다.

**구성**

| 컨테이너 | 하는 일 | 밖에 열림 |
| --- | --- | --- |
| web (nginx) | web 빌드(dist)를 보내고 `/api` 를 server:8080 으로 넘긴다 (web/nginx.conf) | 80 |
| server (Spring) | API. `DB_HOST=db`, `JUDGE_API_URL=http://judge:8000` | X |
| judge (FastAPI) | 판단 채점. 인증이 없어서 절대 밖에 열지 않는다 | X |
| db (PostgreSQL 16) | 데이터. 첫 실행 때 db/migrations 자동 적용 | X |
| scheduler (worker) | `run_daily.py --schedule`, 매일 08:00 KST | X |

**현재 환경**: AWS 무료 플랜(크레딧, 리전은 시드니 ap-southeast-2로 고정), t3.small(2GB) + 스왑 2GB, Ubuntu 24.04, gp3 30GB. 보안 그룹은 22(관리자 IP만)·80. 예산 알림 월 $15.

**처음 배포**
1. EC2에 Docker 설치(`curl -fsSL https://get.docker.com | sudo sh`), 스왑 2GB, `timedatectl set-timezone Asia/Seoul`
2. `git clone -b develop https://github.com/capstone-moneymate/moneymate.git`, `.env` 는 scp 로 복사 (git 에 없음)
3. `docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d --build`
4. 데이터 옮기기: 로컬 `pg_dump -Fc` → EC2 db 컨테이너에서 `pg_restore --clean --if-exists --no-owner`

**코드 업데이트**: EC2에서 `git pull` 후 3번 명령을 다시 실행한다.

**주의할 점**
- `NEWS_INCLUDE_PENDING=true`(기본값): 검수 전 pending 카드도 보인다. 검수 후 `.env` 에 `NEWS_INCLUDE_PENDING=false`.
- HTTP(IP 주소)로 시연하므로 `SESSION_COOKIE_SECURE=false`. HTTPS 를 붙이면 true.
- scheduler 는 매일 Claude 를 부른다. 비용 상한은 `.env` 의 `LLM_MONTHLY_LIMIT_USD`.
- 기술확정안의 S3 + CloudFront, Secrets Manager, GitHub Actions 자동 배포는 하지 않았다 (시간 부족).

**확인 순서**: `docker compose ... ps` 가 모두 Up → `curl http://<IP>/` 200 → `curl http://<IP>/api/news/home?userId=<UUID>` 200 → 다음 날 08:00 뒤 `docker logs moneymate-scheduler`.
