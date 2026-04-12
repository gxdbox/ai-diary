import SwiftUI

struct SplashScreen: View {
    @Binding var isActive: Bool
    @State private var dotOpacity: [Double] = [0.3, 0.3, 0.3]
    @State private var logoScale: CGFloat = 0.8

    var body: some View {
        ZStack {
            // 渐变背景
            LinearGradient(
                colors: [
                    Color(hex: "E8D5F2"),
                    Color(hex: "D5E8F2")
                ],
                startPoint: .topLeading,
                endPoint: .bottomTrailing
            )
            .ignoresSafeArea()

            VStack(spacing: 32) {
                // Logo区域
                ZStack {
                    // 外圈
                    Circle()
                        .stroke(Color(hex: "8B7EC8").opacity(0.3), lineWidth: 3)
                        .frame(width: 120, height: 120)

                    // 内圈填充
                    Circle()
                        .fill(Color(hex: "8B7EC8").opacity(0.15))
                        .frame(width: 100, height: 100)

                    // 日记本图标
                    Image(systemName: "book.fill")
                        .font(.system(size: 40))
                        .foregroundColor(Color(hex: "8B7EC8"))

                    // AI 元素（小星星装饰）
                    Image(systemName: "sparkles")
                        .font(.system(size: 16))
                        .foregroundColor(Color(hex: "6BB6D6"))
                        .offset(x: 35, y: -35)
                }
                .scaleEffect(logoScale)
                .onAppear {
                    withAnimation(.easeOut(duration: 0.6)) {
                        logoScale = 1.0
                    }
                }

                // App名称
                Text("AI日记")
                    .font(.system(size: 28, weight: .semibold, design: .rounded))
                    .foregroundColor(Color(hex: "1A1918"))

                Spacer()
                    .frame(height: 60)

                // 加载动画（三个跳动的圆点）
                HStack(spacing: 8) {
                    ForEach(0..<3, id: \.self) { index in
                        Circle()
                            .fill(Color(hex: "8B7EC8"))
                            .frame(width: 8, height: 8)
                            .opacity(dotOpacity[index])
                    }
                }
                .onAppear {
                    startDotAnimation()
                }

                // 版本号
                Text("v1.0.0")
                    .font(.system(size: 12))
                    .foregroundColor(Color(hex: "9C9B99").opacity(0.6))
                    .padding(.top, 16)
            }
        }
        .onAppear {
            // 2秒后自动消失
            DispatchQueue.main.asyncAfter(deadline: .now() + 2) {
                withAnimation(.easeOut(duration: 0.3)) {
                    isActive = false
                }
            }
        }
    }

    private func startDotAnimation() {
        // 依次点亮每个圆点
        for i in 0..<3 {
            DispatchQueue.main.asyncAfter(deadline: .now() + Double(i) * 0.2) {
                withAnimation(.easeInOut(duration: 0.3).repeatForever(autoreverses: true)) {
                    dotOpacity[i] = 1.0
                }
            }
        }
    }
}

#Preview {
    SplashScreen(isActive: .constant(false))
}