export default {
  extends: ['@commitlint/config-conventional'],
  rules: {
    // CONVENTION.md 1. 커밋 컨벤션의 12종 타입
    'type-enum': [
      2,
      'always',
      [
        'feat',
        'fix',
        'docs',
        'style',
        'design',
        'test',
        'refactor',
        'ci',
        'perf',
        'chore',
        'rename',
        'remove',
      ],
    ],
    'type-case': [2, 'always', 'lower-case'],
    // 메시지는 한글이므로 대소문자 규칙을 끈다
    'subject-case': [0],
  },
}
