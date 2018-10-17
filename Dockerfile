FROM gcr.io/google-appengine/openjdk:8

COPY build/libs/*.jar hellodropwizard.jar

EXPOSE 8080

CMD [ "java", "-jar","hellodropwizard.jar", "server" ]
