rootProject.name = "aero-forge"

pluginManagement {
    repositories {
        maven {
            name = "GTNH Maven"
            url = uri("https://nexus.gtnewhorizons.com/repository/public/")
            mavenContent {
                includeGroupByRegex("com\\.gtnewhorizons\\..+")
                includeGroup("com.gtnewhorizons")
            }
        }
        gradlePluginPortal()
        mavenCentral()
    }
}

plugins {
    // Tự tải JDK 8 cho toolchain, khỏi cài tay trên CI.
    id("org.gradle.toolchains.foojay-resolver-convention") version "1.0.0"
}
