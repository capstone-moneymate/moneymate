-- 시도 번호 통합 테스트 (#215). 카드 1: 개념 → 퀴즈 → 차트 → 판단, 카드 2: 퀴즈 두 개
INSERT INTO cards (id, card_date, card_type, status, title, slides)
VALUES (1, '2026-11-20', 1, 'published', '시도 번호 카드 1', '[]'),
       (2, '2026-11-20', 1, 'published', '시도 번호 카드 2', '[]');

INSERT INTO steps (id, card_id, step_no, kind, content)
VALUES (101, 1, 1, 'concept', '{}'),
       (102, 1, 2, 'quiz', '{}'),
       (103, 1, 3, 'chart', '{}'),
       (104, 1, 4, 'judgement', '{}'),
       (201, 2, 1, 'quiz', '{}'),
       (202, 2, 2, 'quiz', '{}');
