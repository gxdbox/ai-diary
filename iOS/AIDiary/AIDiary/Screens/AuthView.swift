import SwiftUI

/// 认证页面容器 — 根据状态切换登录/注册
struct AuthView: View {
    @EnvironmentObject var authService: AuthService
    @State private var showRegister = false

    var body: some View {
        ZStack {
            Color(hex: "F5F4F1")
                .ignoresSafeArea()

            VStack(spacing: 0) {
                Spacer()

                // Logo 区域
                VStack(spacing: 12) {
                    Circle()
                        .fill(Color(hex: "C4935A"))
                        .frame(width: 72, height: 72)
                        .overlay(
                            Image(systemName: "book.fill")
                                .font(.system(size: 30))
                                .foregroundColor(.white)
                        )

                    Text("AI 智能日记")
                        .font(.system(size: 22, weight: .semibold))
                        .foregroundColor(Color(hex: "1A1918"))

                    Text("珍藏每一颗记忆")
                        .font(.system(size: 14))
                        .foregroundColor(Color(hex: "6D6C6A"))
                }

                Spacer()

                // 表单区域
                if showRegister {
                    RegisterView(authService: authService) {
                        withAnimation(.easeInOut(duration: 0.25)) {
                            showRegister = false
                        }
                    }
                } else {
                    LoginView(authService: authService) {
                        withAnimation(.easeInOut(duration: 0.25)) {
                            showRegister = true
                        }
                    }
                }

                Spacer()
            }
            .padding(.horizontal, 24)
        }
    }
}

// MARK: - 登录视图

private struct LoginView: View {
    let authService: AuthService
    let onSwitchToRegister: () -> Void

    @State private var email = ""
    @State private var password = ""

    var body: some View {
        VStack(spacing: 16) {
            // 邮箱
            VStack(alignment: .leading, spacing: 8) {
                Text("邮箱")
                    .font(.system(size: 13))
                    .foregroundColor(Color(hex: "6D6C6A"))

                TextField("请输入邮箱", text: $email)
                    .font(.system(size: 16))
                    .keyboardType(.emailAddress)
                    .textContentType(.emailAddress)
                    .autocapitalization(.none)
                    .disableAutocorrection(true)
                    .padding(.horizontal, 16)
                    .frame(height: 50)
                    .background(Color.white)
                    .cornerRadius(12)
                    .overlay(
                        RoundedRectangle(cornerRadius: 12)
                            .stroke(Color(hex: "E5E4E1"), lineWidth: 1)
                    )
            }

            // 密码
            VStack(alignment: .leading, spacing: 8) {
                Text("密码")
                    .font(.system(size: 13))
                    .foregroundColor(Color(hex: "6D6C6A"))

                SecureField("请输入密码", text: $password)
                    .font(.system(size: 16))
                    .textContentType(.password)
                    .padding(.horizontal, 16)
                    .frame(height: 50)
                    .background(Color.white)
                    .cornerRadius(12)
                    .overlay(
                        RoundedRectangle(cornerRadius: 12)
                            .stroke(Color(hex: "E5E4E1"), lineWidth: 1)
                    )
            }

            // 错误信息
            if let error = authService.errorMessage {
                Text(error)
                    .font(.system(size: 13))
                    .foregroundColor(Color(hex: "D08068"))
                    .frame(maxWidth: .infinity, alignment: .leading)
            }

            // 登录按钮
            Button {
                Task {
                    await authService.login(email: email, password: password)
                }
            } label: {
                Group {
                    if authService.isLoading {
                        ProgressView()
                            .tint(.white)
                    } else {
                        Text("登录")
                            .font(.system(size: 16, weight: .semibold))
                    }
                }
                .frame(maxWidth: .infinity)
                .frame(height: 50)
                .background(Color(hex: "C4935A"))
                .foregroundColor(.white)
                .cornerRadius(12)
            }
            .disabled(authService.isLoading || email.isEmpty || password.isEmpty)

            // 切换到注册
            HStack(spacing: 4) {
                Text("还没有账号？")
                    .font(.system(size: 14))
                    .foregroundColor(Color(hex: "6D6C6A"))

                Button("注册") {
                    onSwitchToRegister()
                }
                .font(.system(size: 14, weight: .medium))
                .foregroundColor(Color(hex: "C4935A"))
            }
        }
    }
}

// MARK: - 注册视图

private struct RegisterView: View {
    let authService: AuthService
    let onSwitchToLogin: () -> Void

    @State private var email = ""
    @State private var password = ""
    @State private var confirmPassword = ""
    @State private var nickname = ""
    @State private var passwordMismatch = false

    var body: some View {
        VStack(spacing: 16) {
            // 邮箱
            VStack(alignment: .leading, spacing: 8) {
                Text("邮箱")
                    .font(.system(size: 13))
                    .foregroundColor(Color(hex: "6D6C6A"))

                TextField("请输入邮箱", text: $email)
                    .font(.system(size: 16))
                    .keyboardType(.emailAddress)
                    .textContentType(.emailAddress)
                    .autocapitalization(.none)
                    .disableAutocorrection(true)
                    .padding(.horizontal, 16)
                    .frame(height: 50)
                    .background(Color.white)
                    .cornerRadius(12)
                    .overlay(
                        RoundedRectangle(cornerRadius: 12)
                            .stroke(Color(hex: "E5E4E1"), lineWidth: 1)
                    )
            }

            // 昵称（可选）
            VStack(alignment: .leading, spacing: 8) {
                Text("昵称（可选）")
                    .font(.system(size: 13))
                    .foregroundColor(Color(hex: "6D6C6A"))

                TextField("给自己取个名字", text: $nickname)
                    .font(.system(size: 16))
                    .padding(.horizontal, 16)
                    .frame(height: 50)
                    .background(Color.white)
                    .cornerRadius(12)
                    .overlay(
                        RoundedRectangle(cornerRadius: 12)
                            .stroke(Color(hex: "E5E4E1"), lineWidth: 1)
                    )
            }

            // 密码
            VStack(alignment: .leading, spacing: 8) {
                Text("密码")
                    .font(.system(size: 13))
                    .foregroundColor(Color(hex: "6D6C6A"))

                SecureField("请输入密码", text: $password)
                    .font(.system(size: 16))
                    .textContentType(.newPassword)
                    .padding(.horizontal, 16)
                    .frame(height: 50)
                    .background(Color.white)
                    .cornerRadius(12)
                    .overlay(
                        RoundedRectangle(cornerRadius: 12)
                            .stroke(Color(hex: "E5E4E1"), lineWidth: 1)
                    )
            }

            // 确认密码
            VStack(alignment: .leading, spacing: 8) {
                Text("确认密码")
                    .font(.system(size: 13))
                    .foregroundColor(Color(hex: "6D6C6A"))

                SecureField("再次输入密码", text: $confirmPassword)
                    .font(.system(size: 16))
                    .textContentType(.newPassword)
                    .padding(.horizontal, 16)
                    .frame(height: 50)
                    .background(Color.white)
                    .cornerRadius(12)
                    .overlay(
                        RoundedRectangle(cornerRadius: 12)
                            .stroke(passwordMismatch ? Color(hex: "D08068") : Color(hex: "E5E4E1"), lineWidth: 1)
                    )
            }

            // 错误信息
            if let error = authService.errorMessage {
                Text(error)
                    .font(.system(size: 13))
                    .foregroundColor(Color(hex: "D08068"))
                    .frame(maxWidth: .infinity, alignment: .leading)
            }

            // 注册按钮
            Button {
                guard password == confirmPassword else {
                    passwordMismatch = true
                    return
                }
                passwordMismatch = false
                Task {
                    await authService.register(
                        email: email,
                        password: password,
                        nickname: nickname.isEmpty ? nil : nickname
                    )
                }
            } label: {
                Group {
                    if authService.isLoading {
                        ProgressView()
                            .tint(.white)
                    } else {
                        Text("注册")
                            .font(.system(size: 16, weight: .semibold))
                    }
                }
                .frame(maxWidth: .infinity)
                .frame(height: 50)
                .background(Color(hex: "C4935A"))
                .foregroundColor(.white)
                .cornerRadius(12)
            }
            .disabled(authService.isLoading || email.isEmpty || password.isEmpty || confirmPassword.isEmpty)

            // 切换到登录
            HStack(spacing: 4) {
                Text("已有账号？")
                    .font(.system(size: 14))
                    .foregroundColor(Color(hex: "6D6C6A"))

                Button("登录") {
                    onSwitchToLogin()
                }
                .font(.system(size: 14, weight: .medium))
                .foregroundColor(Color(hex: "C4935A"))
            }
        }
    }
}

// MARK: - Preview

#Preview {
    AuthView()
        .environmentObject(AuthService())
}
