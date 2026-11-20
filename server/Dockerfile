# Spring 서버 이미지 (배포용). docker-compose.prod.yml 의 server 서비스가 쓴다.
# 1단계: JDK 로 jar 를 만든다 / 2단계: JRE 만 있는 작은 이미지에서 실행한다
FROM eclipse-temurin:21-jdk AS build
WORKDIR /src

# gradle 래퍼와 설정 먼저 복사해 의존성 층을 캐시한다
COPY gradlew settings.gradle build.gradle ./
COPY gradle gradle
# Windows 에서 체크아웃하면 gradlew 가 CRLF 일 수 있어서 LF 로 바꾼다
RUN sed -i 's/\r$//' gradlew && chmod +x gradlew && ./gradlew --no-daemon dependencies > /dev/null

COPY src src
RUN ./gradlew --no-daemon bootJar -x test && cp build/libs/*-SNAPSHOT.jar /app.jar

FROM eclipse-temurin:21-jre
ENV TZ=Asia/Seoul
COPY --from=build /app.jar /app.jar
EXPOSE 8080
# EC2 t3.small(2GB)에서 DB·채점 서버와 같이 돌아서 힙을 제한한다
ENTRYPOINT ["java", "-Xms128m", "-Xmx512m", "-jar", "/app.jar"]
