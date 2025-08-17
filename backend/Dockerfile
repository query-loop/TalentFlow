FROM gradle:8.8-jdk21-alpine AS build
WORKDIR /home/gradle/src
COPY . .
RUN gradle installDist --no-daemon

FROM eclipse-temurin:21-jre-alpine
WORKDIR /app
COPY --from=build /home/gradle/src/build/install/backend /app
EXPOSE 8080
CMD ["/app/bin/backend"]
