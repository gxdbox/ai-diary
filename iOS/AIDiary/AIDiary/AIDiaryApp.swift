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
        // 初始化 LocationService 并提前请求位置权限
        // 这样权限弹窗会在主界面显示，而不是在 sheet 内
        _ = LocationService.shared
        let status = LocationService.shared.authorizationStatus
        print("📍 App启动 - 位置授权状态: \(status.rawValue)")

        if status == .notDetermined {
            print("📍 App启动 - 未授权，预请求位置权限...")
            // 预请求权限，用户在主界面就能看到弹窗
            LocationService.shared.requestAuthorization()
        }

        print("App 启动完成，缓存服务和位置服务已初始化")
    }
}