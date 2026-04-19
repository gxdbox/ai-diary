import SwiftUI

struct SplashScreen: View {
    @Binding var isActive: Bool
    @State private var dotOpacity: [Double] = [0.3, 0.3, 0.3]
    @State private var logoScale: CGFloat = 0.8

    var body: some View {
        ZStack {
            // 渐变背景（松果色系暖色调）
            LinearGradient(
                colors: [
                    Color(hex: "F5E6D3"),  // 浅棕
                    Color(hex: "E8D5B8")  // 米黄
                ],
                startPoint: .topLeading,
                endPoint: .bottomTrailing
            )
            .ignoresSafeArea()

            VStack(spacing: 32) {
                // 松果 Logo
                ZStack {
                    // 外圈
                    Circle()
                        .stroke(Color(hex: "C4935A").opacity(0.3), lineWidth: 3)
                        .frame(width: 120, height: 120)

                    // 内圈填充
                    Circle()
                        .fill(Color(hex: "C4935A").opacity(0.15))
                        .frame(width: 100, height: 100)

                    // 松果图标（六边形组合）
                    PineconeLogo(size: 40, color: Color(hex: "C4935A"))
                }
                .scaleEffect(logoScale)
                .onAppear {
                    withAnimation(.easeOut(duration: 0.6)) {
                        logoScale = 1.0
                    }
                }

                // App名称
                Text("松果日记")
                    .font(.system(size: 28, weight: .semibold, design: .rounded))
                    .foregroundColor(Color(hex: "1A1918"))

                Spacer()
                    .frame(height: 60)

                // 加载动画（松果形状的圆点）
                HStack(spacing: 8) {
                    ForEach(0..<3, id: \.self) { index in
                        Circle()
                            .fill(Color(hex: "C4935A"))
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

// 松果 Logo 组件
struct PineconeLogo: View {
    let size: CGFloat
    let color: Color

    var body: some View {
        // 用六边形叠加形成松果形状
        ZStack {
            // 顶部鳞片（最小）
            PolygonShape(sides: 6)
                .fill(color.opacity(0.6))
                .frame(width: size * 0.3, height: size * 0.3)
                .offset(y: -size * 0.35)

            // 第二层
            PolygonShape(sides: 6)
                .fill(color.opacity(0.7))
                .frame(width: size * 0.4, height: size * 0.4)
                .offset(y: -size * 0.15)

            // 第三层（中心）
            PolygonShape(sides: 6)
                .fill(color)
                .frame(width: size * 0.5, height: size * 0.5)
                .offset(y: size * 0.05)

            // 第四层
            PolygonShape(sides: 6)
                .fill(color.opacity(0.8))
                .frame(width: size * 0.4, height: size * 0.4)
                .offset(y: size * 0.25)
        }
    }
}

// 多边形形状
struct PolygonShape: Shape {
    let sides: Int

    func path(in rect: CGRect) -> Path {
        var path = Path()
        let center = CGPoint(x: rect.midX, y: rect.midY)
        let radius = min(rect.width, rect.height) / 2

        for i in 0..<sides {
            let angle = Double(i) * 360.0 / Double(sides) - 90
            let radians = angle * .pi / 180.0
            let point = CGPoint(
                x: center.x + radius * CGFloat(__cos(radians)),
                y: center.y + radius * CGFloat(__sin(radians))
            )
            if i == 0 {
                path.move(to: point)
            } else {
                path.addLine(to: point)
            }
        }
        path.closeSubpath()
        return path
    }
}

#Preview {
    SplashScreen(isActive: .constant(false))
}