import Foundation

// MARK: - 用户模型

struct User: Codable, Identifiable {
    let id: Int
    let email: String
    let nickname: String?
    let avatarColor: String

    enum CodingKeys: String, CodingKey {
        case id
        case email
        case nickname
        case avatarColor = "avatar_color"
    }
}

// MARK: - 认证响应

struct TokenResponse: Codable {
    let accessToken: String
    let tokenType: String
    let user: User

    enum CodingKeys: String, CodingKey {
        case accessToken = "access_token"
        case tokenType = "token_type"
        case user
    }
}

// MARK: - 注册请求

struct RegisterRequest: Codable {
    let email: String
    let password: String
    let nickname: String?
}
