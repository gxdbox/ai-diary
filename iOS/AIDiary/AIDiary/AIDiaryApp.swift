import SwiftUI
import Combine
import CoreLocation

@main
struct AIDiaryApp: App {
    @StateObject private var appState = AppState()
    @State private var showSplash = true

    var body: some Scene {
        WindowGroup {
            ZStack {
                if showSplash {
                    SplashScreen(isActive: $showSplash)
                } else {
                    ContentView()
                        .environmentObject(appState)
                        .preferredColorScheme(.light)
                        .task {
                            await appState.setup()
                        }
                }
            }
        }
    }
}

@MainActor
class AppState: ObservableObject {
    func setup() async {
        await CacheService.shared.setup()
        _ = LocationService.shared

        // 如果位置服务启用且未授权，预请求权限
        if CLLocationManager.locationServicesEnabled() {
            if LocationService.shared.authorizationStatus == .notDetermined {
                LocationService.shared.requestAuthorization()
            }
        }
    }
}