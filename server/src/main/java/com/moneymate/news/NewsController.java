package com.moneymate.news;

import com.moneymate.news.NewsDtos.CardDetail;
import com.moneymate.news.NewsDtos.NewsHome;
import java.util.Map;
import java.util.UUID;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.ExceptionHandler;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;

/** 탭1 뉴스 홈과 카드 상세 API. C의 탭1 화면(web/src/api/news.ts, cards.ts)이 부른다. */
@RestController
public class NewsController {

    private final NewsService service;

    public NewsController(NewsService service) {
        this.service = service;
    }

    /** 지수 4개 + 오늘의 카드. userId 를 주면 학습을 끝낸 카드 id(completedCardIds)도 채운다. */
    @GetMapping("/api/news/home")
    public NewsHome home(@RequestParam(required = false) UUID userId) {
        return service.home(userId == null ? null : userId.toString());
    }

    /** 카드뉴스 slides + 단계 steps. 정답은 내려보내지 않는다. */
    @GetMapping("/api/cards/{id}")
    public CardDetail card(@PathVariable long id) {
        return service.card(id);
    }

    @ExceptionHandler(NewsService.CardNotFound.class)
    ResponseEntity<Map<String, String>> cardNotFound(NewsService.CardNotFound e) {
        return ResponseEntity.status(HttpStatus.NOT_FOUND).body(Map.of("message", e.getMessage()));
    }
}
