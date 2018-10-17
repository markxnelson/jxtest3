package com.wercker.example.hellohelidon.resources;

import com.wercker.example.hellohelidon.api.AppVersion;

import javax.json.Json;
import javax.json.JsonObject;

import io.helidon.config.Config;
import io.helidon.webserver.Routing;
import io.helidon.webserver.ServerRequest;
import io.helidon.webserver.ServerResponse;
import io.helidon.webserver.Service;

public class AppVersionService implements Service {

    /**
     * A service registers itself by updating the routine rules.
     * @param rules the routing rules.
     */
    @Override
    public final void update(final Routing.Rules rules) {
        rules
            .get(this::getVersion);
    }

    /**
     * Return a greeting message using the name that was provided.
     * @param request the server request
     * @param response the server response
     */
    private void getVersion(final ServerRequest request,
                            final ServerResponse response) {

        JsonObject returnObject = Json.createObjectBuilder()
                .add("version", new AppVersion().getVersion())
                .build();
        response.send(returnObject);
    }
}
