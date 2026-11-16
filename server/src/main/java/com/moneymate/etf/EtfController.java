package com.moneymate.etf;

import com.moneymate.etf.EtfDtos.EtfDaily;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RestController;

/** 탭2 액티브 ETF "어제 움직인 종목" API. 읽기 전용이다. */
@RestController
public class EtfController {

    private final EtfService service;

    public EtfController(EtfService service) {
        this.service = service;
    }

    /** ETF 마다 최신 스냅샷의 어제 변화: 함께 늘림, 가장 많이 늘림·줄임. */
    @GetMapping("/api/etf/daily")
    public EtfDaily daily() {
        return service.daily();
    }
}
