package com.moneymate.judgement;

import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.security.NoSuchAlgorithmException;
import java.util.HexFormat;

/**
 * 같은 답안을 알아보는 해시. user_answers.answer_hash 에 저장한다.
 * 단계 id + 답안을 SHA-256 으로. 앞뒤 공백과 연속 공백·줄바꿈 차이는 같은 답안으로 본다.
 * 선택지(choice)는 채점하지 않으므로 해시에 넣지 않는다.
 */
public final class AnswerHasher {

    private AnswerHasher() {
    }

    public static String normalize(String answer) {
        return answer == null ? "" : answer.strip().replaceAll("\\s+", " ");
    }

    public static String hash(long stepId, String answer) {
        try {
            MessageDigest sha = MessageDigest.getInstance("SHA-256");
            byte[] digest = sha.digest((stepId + "\n" + normalize(answer)).getBytes(StandardCharsets.UTF_8));
            return HexFormat.of().formatHex(digest);
        } catch (NoSuchAlgorithmException e) {
            throw new IllegalStateException("SHA-256 을 쓸 수 없어요", e);
        }
    }
}
