package com.moneymate.overlap;

import com.moneymate.overlap.OverlapDtos.OverlapList;
import com.moneymate.overlap.OverlapDtos.StockOverlap;
import java.util.Map;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.ExceptionHandler;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.RestController;

/** 탭2 겹침 메인 상단과 종목 상세 API. 읽기 전용이다. */
@RestController
public class OverlapController {

    private final OverlapService service;

    public OverlapController(OverlapService service) {
        this.service = service;
    }

    /** 가장 최근 계산일의 겹침 종목 목록 (티커 순). */
    @GetMapping("/api/overlaps")
    public OverlapList list() {
        return service.list();
    }

    /** 종목 하나의 큰손 변화·ETF 추세·방향 비교. 겹침 결과에 없으면 404. */
    @GetMapping("/api/stocks/{ticker}")
    public StockOverlap stock(@PathVariable String ticker) {
        return service.stock(ticker);
    }

    @ExceptionHandler(OverlapService.StockNotFound.class)
    ResponseEntity<Map<String, String>> stockNotFound(OverlapService.StockNotFound e) {
        return ResponseEntity.status(HttpStatus.NOT_FOUND).body(Map.of("message", e.getMessage()));
    }
}
