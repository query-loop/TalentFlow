package com.talentflow

import io.ktor.server.application.*
import io.ktor.server.engine.*
import io.ktor.server.netty.*
import io.ktor.server.response.*
import io.ktor.server.request.*
import io.ktor.server.routing.*
import io.ktor.serialization.kotlinx.json.*
import io.ktor.server.plugins.contentnegotiation.*
import io.ktor.http.*
import io.ktor.server.plugins.cors.routing.*

fun main() {
    embeddedServer(Netty, port = 8080) {
        install(ContentNegotiation) { json() }
        install(CORS) {
            allowHost("localhost:5173")
            allowHeader(HttpHeaders.ContentType)
            allowHeader(HttpHeaders.Authorization)
            allowMethod(HttpMethod.Get)
            allowMethod(HttpMethod.Post)
            allowMethod(HttpMethod.Put)
            allowMethod(HttpMethod.Delete)
        }
        routing {
            // Simple health-like text
            get("/ping") { call.respondText("pong") }
            get("/api/health") { call.respond(mapOf("status" to "ok")) }
            // Plain text resume status
            get("/resume") { call.respondText("your resume has been curating...", ContentType.Text.Plain) }
            // Endpoint listing for quick inspection
            get("/api/endpoints") {
                val endpoints = listOf(
                    mapOf("method" to "GET", "path" to "/", "description" to "Welcome"),
                    mapOf("method" to "GET", "path" to "/ping", "description" to "Ping response"),
                    mapOf("method" to "GET", "path" to "/api/health", "description" to "Health status JSON"),
                    mapOf("method" to "GET", "path" to "/resume", "description" to "Resume curating text"),
                    mapOf("method" to "GET", "path" to "/api/endpoints", "description" to "This list")
                )
                call.respond(endpoints)
            }
            // Root welcome
            get("/") { call.respondText("TalentFlow backend is running") }
        }
    }.start(wait = true)
}
