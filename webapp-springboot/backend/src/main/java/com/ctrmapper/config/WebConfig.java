package com.ctrmapper.config;

import org.springframework.context.annotation.Configuration;
import org.springframework.core.io.ClassPathResource;
import org.springframework.core.io.Resource;
import org.springframework.web.servlet.config.annotation.CorsRegistry;
import org.springframework.web.servlet.config.annotation.ResourceHandlerRegistry;
import org.springframework.web.servlet.config.annotation.WebMvcConfigurer;
import org.springframework.web.servlet.resource.PathResourceResolver;

import java.io.IOException;

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
        // Serve Vue.js frontend assets from frontend-dist
        registry.addResourceHandler("/assets/**")
                .addResourceLocations("file:../frontend-dist/assets/", "classpath:/static/assets/");

        // Serve other static files but don't intercept API routes
        registry.addResourceHandler("/*.js", "/*.css", "/*.ico", "/*.png", "/*.svg")
                .addResourceLocations("file:../frontend-dist/", "classpath:/static/");
    }
}
