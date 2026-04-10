import SwiftUI
import Combine

@main
struct AIDiaryApp: App {
    @StateObject private var appState = AppState()
    
    var body: some Scene {
        WindowGroup {
            ContentView()
                .environmentObject(appState)
                .preferredColorScheme(.light)  // 强制使用浅色模式
                .task {
                    await appState.setup()
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