package com.moneymate.answer;

import jakarta.validation.Valid;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

/** 탭1 코드 채점 답안 API (퀴즈·차트 읽기·인과 순서). 판단해보기는 /api/judgement. */
@RestController
@RequestMapping("/api/answers")
public class AnswerController {

    private final AnswerService service;

    public AnswerController(AnswerService service) {
        this.service = service;
    }

    @PostMapping
    public AnswerResult submit(@Valid @RequestBody AnswerRequest request) {
        return service.submit(request);
    }
}
