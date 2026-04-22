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

        // 初始化 LocationService
        _ = LocationService.shared

        // 检查系统位置服务是否启用
        let locationEnabled = CLLocationManager.locationServicesEnabled()
        print("📍 系统位置服务是否启用: \(locationEnabled)")

        if !locationEnabled {
            print("📍 ❌ 系统位置服务被禁用，请在设置中开启")
            print("App 启动完成（位置服务不可用）")
            return
        }

        let status = LocationService.shared.authorizationStatus
        print("📍 App启动 - 位置授权状态: \(status.rawValue)")

        if status == .notDetermined {
            print("📍 App启动 - 未授权，预请求位置权限...")
            LocationService.shared.requestAuthorization()
        }

        print("App 启动完成，缓存服务和位置服务已初始化")
    }
}