plugins { id("com.android.application"); id("org.jetbrains.kotlin.android") }
android {
    namespace = "com.veilbreaker.companion"
    compileSdk = 35
    defaultConfig {
        applicationId = "com.veilbreaker.companion"
        minSdk = 29
        targetSdk = 35
        versionCode = 6
        versionName = "0.5.1-dev"
    }
    compileOptions { sourceCompatibility = JavaVersion.VERSION_17; targetCompatibility = JavaVersion.VERSION_17 }
    kotlinOptions { jvmTarget = "17" }
    sourceSets["main"].assets.srcDir("../../src/veilbreaker/assets/cellular")
}
dependencies {
    testImplementation("junit:junit:4.13.2")
    testImplementation("org.json:json:20240303")
}
