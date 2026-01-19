package com.ctrmapper;

import org.apache.poi.util.IOUtils;
import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;
import org.springframework.scheduling.annotation.EnableAsync;

@SpringBootApplication
@EnableAsync
public class CtrMapperApplication {

    public static void main(String[] args) {
        // Increase Apache POI max byte array size for large Excel files (500MB)
        IOUtils.setByteArrayMaxOverride(500_000_000);

        SpringApplication.run(CtrMapperApplication.class, args);
        System.out.println("=".repeat(60));
        System.out.println("CTR Mapper Spring Boot Application");
        System.out.println("=".repeat(60));
        System.out.println("Application running on http://localhost:8080");
        System.out.println("API documentation: http://localhost:8080/swagger-ui.html");
        System.out.println("=".repeat(60));
    }
}
