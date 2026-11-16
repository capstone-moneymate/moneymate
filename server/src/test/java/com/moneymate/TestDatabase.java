package com.moneymate;

import java.io.IOException;
import java.io.UncheckedIOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.stream.Stream;
import org.testcontainers.postgresql.PostgreSQLContainer;
import org.testcontainers.utility.MountableFile;

/** 통합 테스트용 PostgreSQL 16. 빈 DB 에 db/migrations 와 fixture SQL 하나를 넣는다. */
public final class TestDatabase {

    /** gradle 테스트는 server/ 에서 돈다 */
    static final Path MIGRATIONS = Path.of("..", "db", "migrations");

    private TestDatabase() {
    }

    /**
     * 빈 DB 가 처음 뜰 때 /docker-entrypoint-initdb.d 의 파일이 이름 순서로 실행된다 (docker-compose.yml 과 같은 방식).
     * fixture 는 마이그레이션 뒤에 돌도록 900_ 을 붙인다.
     */
    public static PostgreSQLContainer postgres(String fixtureResource) {
        PostgreSQLContainer c = new PostgreSQLContainer("postgres:16");
        try (Stream<Path> files = Files.list(MIGRATIONS)) {
            files.filter(p -> p.toString().endsWith(".sql")).forEach(p -> c.withCopyFileToContainer(
                    MountableFile.forHostPath(p), "/docker-entrypoint-initdb.d/" + p.getFileName()));
        } catch (IOException e) {
            throw new UncheckedIOException(e);
        }
        return c.withCopyFileToContainer(MountableFile.forClasspathResource(fixtureResource),
                "/docker-entrypoint-initdb.d/900_fixture.sql");
    }
}
