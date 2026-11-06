package com.moneymate.judgement;

import jakarta.validation.Valid;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

/** 판단해보기 근거 채점 API. C의 판단해보기 화면이 부른다. */
@RestController
@RequestMapping("/api/judgement")
public class JudgementController {

    private final JudgementService service;

    public JudgementController(JudgementService service) {
        this.service = service;
    }

    @PostMapping
    public JudgementResponse judge(@Valid @RequestBody JudgementRequest request) {
        return service.judge(request);
    }
}
