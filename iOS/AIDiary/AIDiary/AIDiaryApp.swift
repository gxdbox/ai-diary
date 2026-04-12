import SwiftUI
import Combine

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
        print("App 启动完成，缓存服务已初始化")
    }
}