# CTR Mapper Spring Boot - Backend Code Reference

## Project Structure

```
webapp-springboot/
├── backend/
│   ├── pom.xml                                    # Maven dependencies
│   ├── src/main/resources/
│   │   └── application.properties                 # App configuration
│   └── src/main/java/com/ctrmapper/
│       ├── CtrMapperApplication.java              # Main entry point
│       ├── config/
│       │   ├── WebConfig.java                     # CORS & static files
│       │   └── AsyncConfig.java                   # Async thread pool
│       ├── controller/
│       │   ├── CtrMapperController.java           # REST API endpoints
│       │   └── FrontendController.java            # Serves index.html
│       ├── model/
│       │   ├── ProcessingRequest.java             # Request DTO
│       │   ├── ProcessingResponse.java            # Response DTO
│       │   ├── JobStatus.java                     # Job tracking DTO
│       │   └── CompanyCodesResponse.java          # Company codes DTO
│       └── service/
│           ├── ExcelProcessorService.java         # Excel processing logic
│           └── FormulaMapper.java                 # Formula calculations
├── frontend-vue/                                  # Vue.js frontend
└── frontend-dist/                                 # Built frontend files
```

---

## 1. pom.xml (Maven Dependencies)

```xml
<?xml version="1.0" encoding="UTF-8"?>
<project xmlns="http://maven.apache.org/POM/4.0.0"
         xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
         xsi:schemaLocation="http://maven.apache.org/POM/4.0.0 https://maven.apache.org/xsd/maven-4.0.0.xsd">
    <modelVersion>4.0.0</modelVersion>

    <parent>
        <groupId>org.springframework.boot</groupId>
        <artifactId>spring-boot-starter-parent</artifactId>
        <version>3.2.0</version>
        <relativePath/>
    </parent>

    <groupId>com.ctrmapper</groupId>
    <artifactId>ctr-mapper</artifactId>
    <version>1.0.0</version>
    <name>CTR Mapper</name>

    <properties>
        <java.version>17</java.version>
    </properties>

    <dependencies>
        <!-- Spring Boot Web -->
        <dependency>
            <groupId>org.springframework.boot</groupId>
            <artifactId>spring-boot-starter-web</artifactId>
        </dependency>

        <!-- Validation -->
        <dependency>
            <groupId>org.springframework.boot</groupId>
            <artifactId>spring-boot-starter-validation</artifactId>
        </dependency>

        <!-- Apache POI for Excel -->
        <dependency>
            <groupId>org.apache.poi</groupId>
            <artifactId>poi</artifactId>
            <version>5.2.5</version>
        </dependency>
        <dependency>
            <groupId>org.apache.poi</groupId>
            <artifactId>poi-ooxml</artifactId>
            <version>5.2.5</version>
        </dependency>

        <!-- Streaming Excel reader (memory efficient for large files) -->
        <dependency>
            <groupId>com.github.pjfanning</groupId>
            <artifactId>excel-streaming-reader</artifactId>
            <version>4.3.0</version>
        </dependency>

        <!-- Lombok (reduces boilerplate) -->
        <dependency>
            <groupId>org.projectlombok</groupId>
            <artifactId>lombok</artifactId>
            <optional>true</optional>
        </dependency>
    </dependencies>

    <build>
        <plugins>
            <plugin>
                <groupId>org.springframework.boot</groupId>
                <artifactId>spring-boot-maven-plugin</artifactId>
            </plugin>
        </plugins>
    </build>
</project>
```

---

## 2. application.properties

```properties
# Server Configuration
server.port=8080

# File Upload Configuration (500MB for large Excel files)
spring.servlet.multipart.max-file-size=500MB
spring.servlet.multipart.max-request-size=500MB

# Upload directory
app.upload-dir=uploads

# Static resources (Vue.js frontend)
spring.web.resources.static-locations=classpath:/static/,file:../frontend-dist/

spring.application.name=CTR Mapper
```

---

## 3. CtrMapperApplication.java (Main Entry Point)

```java
package com.ctrmapper;

import org.apache.poi.util.IOUtils;
import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;
import org.springframework.scheduling.annotation.EnableAsync;

@SpringBootApplication
@EnableAsync
public class CtrMapperApplication {

    public static void main(String[] args) {
        // Increase Apache POI max byte array size for large Excel files
        IOUtils.setByteArrayMaxOverride(500_000_000);

        SpringApplication.run(CtrMapperApplication.class, args);
        System.out.println("=".repeat(60));
        System.out.println("CTR Mapper Spring Boot Application");
        System.out.println("=".repeat(60));
        System.out.println("Application running on http://localhost:8080");
        System.out.println("=".repeat(60));
    }
}
```

---

## 4. Config Classes

### WebConfig.java (CORS & Static Resources)

```java
package com.ctrmapper.config;

import org.springframework.context.annotation.Configuration;
import org.springframework.web.servlet.config.annotation.CorsRegistry;
import org.springframework.web.servlet.config.annotation.ResourceHandlerRegistry;
import org.springframework.web.servlet.config.annotation.WebMvcConfigurer;

@Configuration
public class WebConfig implements WebMvcConfigurer {

    @Override
    public void addCorsMappings(CorsRegistry registry) {
        registry.addMapping("/**")
                .allowedOrigins("*")
                .allowedMethods("GET", "POST", "PUT", "DELETE", "OPTIONS")
                .allowedHeaders("*");
    }

    @Override
    public void addResourceHandlers(ResourceHandlerRegistry registry) {
        // Serve Vue.js frontend assets
        registry.addResourceHandler("/assets/**")
                .addResourceLocations("file:../frontend-dist/assets/", "classpath:/static/assets/");

        registry.addResourceHandler("/*.js", "/*.css", "/*.ico", "/*.png", "/*.svg")
                .addResourceLocations("file:../frontend-dist/", "classpath:/static/");
    }
}
```

### AsyncConfig.java (Thread Pool for Background Processing)

```java
package com.ctrmapper.config;

import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.scheduling.annotation.EnableAsync;
import org.springframework.scheduling.concurrent.ThreadPoolTaskExecutor;

import java.util.concurrent.Executor;

@Configuration
@EnableAsync
public class AsyncConfig {

    @Bean(name = "taskExecutor")
    public Executor taskExecutor() {
        ThreadPoolTaskExecutor executor = new ThreadPoolTaskExecutor();
        executor.setCorePoolSize(2);
        executor.setMaxPoolSize(5);
        executor.setQueueCapacity(100);
        executor.setThreadNamePrefix("ExcelProcessor-");
        executor.initialize();
        return executor;
    }
}
```

---

## 5. Model Classes (DTOs)

### ProcessingRequest.java

```java
package com.ctrmapper.model;

import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class ProcessingRequest {
    @Builder.Default
    private int inputHeaderStart = 27;

    @Builder.Default
    private int inputDataStart = 28;

    @Builder.Default
    private int templateHeaderStart = 1;

    @Builder.Default
    private int templateDataStart = 2;
}
```

### ProcessingResponse.java

```java
package com.ctrmapper.model;

import com.fasterxml.jackson.annotation.JsonProperty;
import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class ProcessingResponse {
    private boolean success;
    private String message;

    @JsonProperty("job_id")  // Match Python API format (snake_case)
    private String jobId;
}
```

### JobStatus.java

```java
package com.ctrmapper.model;

import com.fasterxml.jackson.annotation.JsonProperty;
import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.time.LocalDateTime;
import java.util.Map;

@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class JobStatus {
    @JsonProperty("job_id")
    private String jobId;

    private String status; // pending, processing, completed, failed

    @JsonProperty("created_at")
    private LocalDateTime createdAt;

    @JsonProperty("completed_at")
    private LocalDateTime completedAt;

    private Map<String, Object> result;
    private String error;
}
```

### CompanyCodesResponse.java

```java
package com.ctrmapper.model;

import com.fasterxml.jackson.annotation.JsonProperty;
import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.util.List;

@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class CompanyCodesResponse {
    private boolean success;

    @JsonProperty("company_codes")
    private List<String> companyCodes;

    @JsonProperty("total_count")
    private int totalCount;
}
```

---

## Key Concepts Demonstrated

1. **@SpringBootApplication** - Main entry point with component scanning
2. **@EnableAsync** - Enable asynchronous method execution
3. **@Configuration** - Spring configuration classes
4. **@Data, @Builder** - Lombok annotations to reduce boilerplate
5. **@JsonProperty** - Jackson annotation for JSON field naming (snake_case vs camelCase)
6. **WebMvcConfigurer** - Customize Spring MVC (CORS, static resources)
7. **ThreadPoolTaskExecutor** - Custom thread pool for async processing
