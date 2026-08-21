// Mod Forge 1.12.2 khoá cứng resource pack Aero, build bằng RetroFuturaGradle (RFG)
// — fork ForgeGradle được bảo trì cho 1.7.10/1.12.2 (ForgeGradle 2 đã chết maven).
// Java 8 toolchain (RFG tự tải qua foojay), Gradle 9.5, MCP mappings mặc định.
plugins {
    id("java")
    id("com.gtnewhorizons.retrofuturagradle") version "2.0.2"
}

group = "com.nostalgia.aeroforge"
version = "1.0.0"
base { archivesName.set("aero-forge") }

java {
    toolchain {
        languageVersion.set(JavaLanguageVersion.of(8))
        vendor.set(org.gradle.jvm.toolchain.JvmVendorSpec.AZUL)
    }
}

minecraft {
    mcVersion.set("1.12.2")
    username.set("Developer")
}

tasks.processResources {
    inputs.property("version", project.version.toString())
    filesMatching("mcmod.info") {
        expand("version" to project.version.toString(), "mcversion" to "1.12.2")
    }
}
