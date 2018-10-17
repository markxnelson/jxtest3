package com.wercker.example.hellohelidon.api;

import org.apache.commons.io.IOUtils;

import java.io.IOException;
import java.net.URL;

public class AppVersion {
  private static final URL VERSION_STRING_URL =
      AppVersion.class.getResource("/version.txt");
  private static final String VERSION_STRING;

  static {
    try {
      VERSION_STRING = IOUtils.toString(VERSION_STRING_URL).trim();
    } catch (final IOException e) {
      throw new IllegalStateException(e);
    }
  }

  public AppVersion() {
  }

  public String getVersion() {
    return VERSION_STRING;
  }

}
