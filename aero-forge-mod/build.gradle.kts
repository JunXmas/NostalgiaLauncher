// Mod Forge khoá cứng resource pack Aero, build bằng RetroFuturaGradle (RFG) —
// ForgeGradle 2 đã chết maven. MỘT source build cho nhiều bản qua -PforgeTarget:
//   1122 -> 1.12.2, 189 -> 1.8.9. API resource pack trùng tên MCP giữa 1.8–1.12.
// Java 8 toolchain (RFG tự tải qua foojay). RFG 2.0.2 cần Java 25 để CHẠY Gradle.
plugins {
    id("java")
    id("com.gtnewhorizons.retrofuturagradle") version "2.0.2"
}

val forgeTarget = (project.findProperty("forgeTarget") ?: "1122").toString()
val mcVer = mapOf("1122" to "1.12.2", "189" to "1.8.9")[forgeTarget]
    ?: throw GradleException("Unknown forgeTarget '$forgeTarget' (use 1122 or 189)")

group = "com.nostalgia.aeroforge"
version = "1.0.0"
base { archivesName.set("aero-forge-$forgeTarget") }

java {
    toolchain {
        languageVersion.set(JavaLanguageVersion.of(8))
        vendor.set(org.gradle.jvm.toolchain.JvmVendorSpec.AZUL)
    }
}

minecraft {
    mcVersion.set(mcVer)
    username.set("Developer")
}

tasks.processResources {
    inputs.property("version", project.version.toString())
    inputs.property("mcversion", mcVer)
    filesMatching("mcmod.info") {
        expand("version" to project.version.toString(), "mcversion" to mcVer)
    }
}
