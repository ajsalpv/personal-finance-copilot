import com.android.build.gradle.BaseExtension

allprojects {
    repositories {
        google()
        mavenCentral()
    }
}

subprojects {
    afterEvaluate {
        val extension = project.extensions.findByName("android")
        if (extension != null && extension is com.android.build.gradle.BaseExtension) {
            // Fix namespace issues for older plugins like contacts_service
            if (extension.namespace == null) {
                extension.namespace = "com.callista.app.${project.name.replace("-", "_")}"
            }
            
            // Standardize SDK versions
            extension.compileSdkVersion(35)
            extension.defaultConfig.minSdk = 24
            extension.defaultConfig.targetSdk = 35
            
            // Enforce Java 11 to avoid JVM target conflicts
            extension.compileOptions.sourceCompatibility = JavaVersion.VERSION_11
            extension.compileOptions.targetCompatibility = JavaVersion.VERSION_11
            
            // Surgical fix for AGP 8.0+: Strip 'package' attribute from manifests of plugins
            val manifestFile = project.file("src/main/AndroidManifest.xml")
            if (manifestFile.exists()) {
                val content = manifestFile.readText()
                if (content.contains("package=")) {
                    val newContent = content.replace(Regex("package=\"[^\"]*\""), "")
                    manifestFile.writeText(newContent)
                }
            }
        }
        
        // Also ensure Kotlin JVM target is 11 if the plugin is applied
        tasks.withType<org.jetbrains.kotlin.gradle.tasks.KotlinCompile>().configureEach {
            kotlinOptions {
                jvmTarget = "11"
            }
        }
    }
}

val newBuildDir: Directory = rootProject.layout.buildDirectory.dir("../../build").get()
rootProject.layout.buildDirectory.value(newBuildDir)

subprojects {
    val newSubprojectBuildDir: Directory = newBuildDir.dir(project.name)
    project.layout.buildDirectory.value(newSubprojectBuildDir)
}
subprojects {
    project.evaluationDependsOn(":app")
}

tasks.register<Delete>("clean") {
    delete(rootProject.layout.buildDirectory)
}
