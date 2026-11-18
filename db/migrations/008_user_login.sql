-- 머니메이트 008_user_login.sql  (초안: C, A 확인 필요)
-- 회원가입·로그인 (가벼운 세션 방식, docs/modules/auth_api.md).
-- users.id 는 그대로 브라우저가 만든 UUID 다. 회원가입하면 그 UUID 에 아이디와 비밀번호 해시를 붙인다.
--   login_id      아이디 (영문 소문자·숫자·_ 4~20자, 서버가 검사)
--   password_hash BCrypt 해시. 비밀번호 원문은 저장하지 않는다
-- 둘 다 NULL 이면 익명 사용자, 둘 다 있으면 계정이다.
-- 이미 만든 DB에 적용: docker compose exec -T db psql -U moneymate -d moneymate < db/migrations/008_user_login.sql

BEGIN;

ALTER TABLE users ADD COLUMN login_id TEXT UNIQUE;
ALTER TABLE users ADD COLUMN password_hash TEXT;
ALTER TABLE users ADD CONSTRAINT users_login_pair_check
    CHECK ((login_id IS NULL) = (password_hash IS NULL));

COMMIT;
