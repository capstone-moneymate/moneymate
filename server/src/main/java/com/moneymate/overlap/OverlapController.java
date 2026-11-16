package com.moneymate.overlap;

import com.moneymate.overlap.OverlapDtos.OverlapList;
import com.moneymate.overlap.OverlapDtos.StockDetail;
import java.util.Map;
import java.util.UUID;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.ExceptionHandler;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.RequestParam;
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

    /**
     * 종목 하나의 큰손 변화·ETF 추세·방향 비교(카드 ①), 카드 ②③(reasons, 없으면 null), "내 지도에 있어요".
     * userId 는 선택이다. 없으면 배운 개념 표시만 빠지고, UUID 형식이 아니면 400. 겹침 결과에 없으면 404.
     */
    @GetMapping("/api/stocks/{ticker}")
    public StockDetail stock(@PathVariable String ticker, @RequestParam(required = false) UUID userId) {
        return service.stock(ticker, userId == null ? null : userId.toString());
    }

    @ExceptionHandler(OverlapService.StockNotFound.class)
    ResponseEntity<Map<String, String>> stockNotFound(OverlapService.StockNotFound e) {
        return ResponseEntity.status(HttpStatus.NOT_FOUND).body(Map.of("message", e.getMessage()));
    }
}
