package com.moneymate.learning;

import java.util.LinkedHashSet;
import java.util.Set;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

/**
 * 개념 학습 기록 (B, conventions P17). 채점 결과를 user_concepts(correct, total)에 쌓는 공통 메서드.
 *
 * 코드 채점 답안 API(C, AnswerService)와 판단 채점 API(A, JudgementService)가 채점한 뒤 이 메서드 하나를 불러서,
 * 채점이 두 곳에서 일어나도 기록 기준이 하나가 되게 한다. "맞음" 판정(판단은 60점 이상)은 부르는 쪽이 정해서 넘긴다.
 * 탭3 인과 지도(학습한 개념)와 다시 보는 개념(정답률 낮은 순)이 이 기록을 읽는다.
 */
@Service
public class ConceptResultRecorder {

    private static final Logger log = LoggerFactory.getLogger(ConceptResultRecorder.class);

    private final LearningRepository repository;

    public ConceptResultRecorder(LearningRepository repository) {
        this.repository = repository;
    }

    /**
     * 개념마다 total +1, 맞았으면 correct +1. 같은 단계를 다시 내도 낼 때마다 센다.
     *
     * @param userId     사용자 UUID 문자열
     * @param conceptIds 그 단계의 개념 id. null·빈 배열이면 아무것도 하지 않는다. 같은 id 는 한 번만 센다
     * @param isCorrect  채점 결과. null(판단 채점을 못 함)이면 기록하지 않는다
     * @return 실제로 기록한 개념 수 (사전에 없는 id 는 빠진다)
     */
    @Transactional
    public int recordConceptResult(String userId, String[] conceptIds, Boolean isCorrect) {
        if (isCorrect == null || conceptIds == null) {
            return 0;
        }
        Set<String> ids = new LinkedHashSet<>();
        for (String id : conceptIds) {
            if (id != null && !id.isBlank()) {
                ids.add(id.strip());
            }
        }
        if (ids.isEmpty()) {
            return 0;
        }
        repository.ensureUser(userId);
        String[] unique = ids.toArray(String[]::new);
        int recorded = repository.upsertConceptResults(userId, unique, isCorrect);
        if (recorded < unique.length) {
            // 출제 쪽에서 사전에 없는 id 가 들어온 것. 채점 응답은 깨지 않고 로그만 남긴다
            log.warn("concepts 에 없는 개념 id 가 있어 {}개 중 {}개만 기록했어요: {}", unique.length, recorded, ids);
        }
        return recorded;
    }
}
