import Foundation
import SwiftUI
import Combine

/// 用户认证服务 — 管理登录状态、token 存储、用户信息
@MainActor
class AuthService: ObservableObject {
    @Published var isLoggedIn: Bool = false
    @Published var currentUser: User?
    @Published var isLoading: Bool = false
    @Published var errorMessage: String?

    private let keychain = KeychainService.shared

    /// 当前有效的 JWT token（从 Keychain 读取）
    var token: String? {
        keychain.loadToken()
    }

    // MARK: - 注册

    func register(email: String, password: String, nickname: String?) async -> Bool {
        isLoading = true
        errorMessage = nil

        do {
            let url = URL(string: "\(AppConfig.baseURL)/api/auth/register")!
            var request = URLRequest(url: url)
            request.httpMethod = "POST"
            request.setValue("application/json", forHTTPHeaderField: "Content-Type")

            let body = RegisterRequest(email: email, password: password, nickname: nickname)
            request.httpBody = try JSONEncoder().encode(body)

            let (data, response) = try await URLSession.shared.data(for: request)

            guard let httpResponse = response as? HTTPURLResponse else {
                errorMessage = "服务器响应异常"
                isLoading = false
                return false
            }

            if httpResponse.statusCode == 200 {
                let tokenResponse = try JSONDecoder().decode(TokenResponse.self, from: data)
                keychain.saveToken(tokenResponse.accessToken)
                currentUser = tokenResponse.user
                isLoggedIn = true
                isLoading = false
                return true
            } else {
                let errorResponse = try? JSONDecoder().decode(ErrorResponse.self, from: data)
                errorMessage = errorResponse?.detail ?? "注册失败"
                isLoading = false
                return false
            }
        } catch {
            errorMessage = "网络错误：\(error.localizedDescription)"
            isLoading = false
            return false
        }
    }

    // MARK: - 登录

    func login(email: String, password: String) async -> Bool {
        isLoading = true
        errorMessage = nil

        do {
            let url = URL(string: "\(AppConfig.baseURL)/api/auth/login")!
            var request = URLRequest(url: url)
            request.httpMethod = "POST"
            request.setValue("application/x-www-form-urlencoded", forHTTPHeaderField: "Content-Type")

            // OAuth2PasswordRequestForm 格式: username=email&password=xxx
            let body = "username=\(email.addingPercentEncoding(withAllowedCharacters: .urlQueryAllowed) ?? email)&password=\(password.addingPercentEncoding(withAllowedCharacters: .urlQueryAllowed) ?? password)"
            request.httpBody = body.data(using: .utf8)

            let (data, response) = try await URLSession.shared.data(for: request)

            guard let httpResponse = response as? HTTPURLResponse else {
                errorMessage = "服务器响应异常"
                isLoading = false
                return false
            }

            if httpResponse.statusCode == 200 {
                let tokenResponse = try JSONDecoder().decode(TokenResponse.self, from: data)
                keychain.saveToken(tokenResponse.accessToken)
                currentUser = tokenResponse.user
                isLoggedIn = true
                isLoading = false
                return true
            } else {
                let errorResponse = try? JSONDecoder().decode(ErrorResponse.self, from: data)
                errorMessage = errorResponse?.detail ?? "登录失败"
                isLoading = false
                return false
            }
        } catch {
            errorMessage = "网络错误：\(error.localizedDescription)"
            isLoading = false
            return false
        }
    }

    // MARK: - 退出登录

    func logout() {
        keychain.deleteToken()
        currentUser = nil
        isLoggedIn = false
        errorMessage = nil
    }

    // MARK: - 获取当前用户信息

    func fetchMe() async {
        guard let token = token else {
            isLoggedIn = false
            return
        }

        do {
            let url = URL(string: "\(AppConfig.baseURL)/api/auth/me")!
            var request = URLRequest(url: url)
            request.httpMethod = "GET"
            request.setValue("Bearer \(token)", forHTTPHeaderField: "Authorization")

            let (data, response) = try await URLSession.shared.data(for: request)

            guard let httpResponse = response as? HTTPURLResponse else { return }

            if httpResponse.statusCode == 200 {
                currentUser = try JSONDecoder().decode(User.self, from: data)
                isLoggedIn = true
            } else {
                // Token 无效或过期
                logout()
            }
        } catch {
            // 网络错误，保持当前状态
        }
    }

    // MARK: - 启动时检查登录状态

    func checkAuthStatus() async {
        guard token != nil else {
            isLoggedIn = false
            return
        }
        await fetchMe()
    }
}

// MARK: - 错误响应模型

private struct ErrorResponse: Decodable {
    let detail: String
}
