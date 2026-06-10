import Foundation

enum AppEnvironment {
    case development
    case production

    var baseURL: String {
        switch self {
        case .development:
            return "http://192.168.0.2:8000"  // 本地开发
        case .production:
            return "https://51pic.xyz"  // 生产环境
        }
    }
}

struct AppConfig {
    // 当前环境：开发时用 .development，发布时改为 .production
    static let environment: AppEnvironment = .production

    static var baseURL: String {
        environment.baseURL
    }
}