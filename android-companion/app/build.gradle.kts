plugins { id("com.android.application"); id("org.jetbrains.kotlin.android") }
android {
    namespace = "com.veilbreaker.companion"
    compileSdk = 35
    defaultConfig {
        applicationId = "com.veilbreaker.companion"
        minSdk = 29
        targetSdk = 35
        versionCode = 3
        versionName = "0.3.0-dev"
    }
    compileOptions { sourceCompatibility = JavaVersion.VERSION_17; targetCompatibility = JavaVersion.VERSION_17 }
    kotlinOptions { jvmTarget = "17" }
}
dependencies {
    testImplementation("junit:junit:4.13.2")
    testImplementation("org.json:json:20240303")
}
