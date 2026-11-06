package com.moneymate;

import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;
import org.springframework.boot.context.properties.ConfigurationPropertiesScan;

/** 머니메이트 API 서버 시작점. 공통 파일: A만 수정한다. 기능은 com.moneymate.<기능> 패키지에 둔다. */
@SpringBootApplication
@ConfigurationPropertiesScan
public class MoneymateApplication {

    public static void main(String[] args) {
        SpringApplication.run(MoneymateApplication.class, args);
    }
}
