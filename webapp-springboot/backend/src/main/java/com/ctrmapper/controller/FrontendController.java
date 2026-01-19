package com.ctrmapper.controller;

import org.springframework.core.io.FileSystemResource;
import org.springframework.core.io.Resource;
import org.springframework.http.MediaType;
import org.springframework.http.ResponseEntity;
import org.springframework.stereotype.Controller;
import org.springframework.web.bind.annotation.GetMapping;

import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.Paths;

@Controller
public class FrontendController {

    @GetMapping("/")
    public ResponseEntity<Resource> serveIndex() {
        // Try to serve from frontend-dist directory
        Path frontendPath = Paths.get("../frontend-dist/index.html");

        if (Files.exists(frontendPath)) {
            return ResponseEntity.ok()
                    .contentType(MediaType.TEXT_HTML)
                    .body(new FileSystemResource(frontendPath));
        }

        // Try alternative path (when running from different directory)
        Path altPath = Paths.get("frontend-dist/index.html");
        if (Files.exists(altPath)) {
            return ResponseEntity.ok()
                    .contentType(MediaType.TEXT_HTML)
                    .body(new FileSystemResource(altPath));
        }

        return ResponseEntity.notFound().build();
    }
}
