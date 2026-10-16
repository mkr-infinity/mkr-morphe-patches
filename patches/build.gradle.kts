// Copyright (c) 2026 mkr-infinity (https://github.com/mkr-infinity/mkr-morphe-patches)
// Personal Morphe-compatible Android patches

group = "app.mkr"

patches {
    about {
        name = "MKR Morphe Patches"
        description = "Personal Morphe-compatible Android patches with automatic patch updates and on-demand APK builds."
        source = "https://github.com/mkr-infinity/mkr-morphe-patches"
        author = "mkr-infinity"
        contact = "https://github.com/mkr-infinity"
        website = "https://github.com/mkr-infinity/mkr-morphe-patches"
        license = "GPLv3"
    }
}

// Separate configuration so gson is available at runtime for the
// generatePatchesList task but never bundled into the APK.
val patchListGeneratorClasspath = configurations.create("patchListGeneratorClasspath")

dependencies {
    compileOnly(libs.gson)
    patchListGeneratorClasspath(libs.gson)
}

tasks {
    register<JavaExec>("generatePatchesList") {
        description = "Build patch with patch list"

        dependsOn(build)

        classpath = sourceSets["main"].runtimeClasspath + patchListGeneratorClasspath
        mainClass.set("util.PatchListGeneratorKt")
    }

    // Used by gradle-semantic-release-plugin.
    publish {
        dependsOn("generatePatchesList")
    }
}
