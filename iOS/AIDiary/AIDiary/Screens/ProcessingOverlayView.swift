import SwiftUI

/// AI 处理等待界面 - 展示金句让等待更有意义
struct ProcessingOverlayView: View {
    @State private var currentQuote: Quote = QuoteLibrary.randomQuote()
    @State private var showQuote = false
    @State private var animationPhase = 0
    @State private var quoteTimer: Timer? = nil

    var body: some View {
        VStack(spacing: 0) {
            Spacer()

            // 金句卡片（主体）
            if showQuote {
                quoteCard
                    .transition(.opacity.combined(with: .scale(scale: 0.95)))
            }

            Spacer()

            // 底部 Loading 区域
            VStack(spacing: 12) {
                // 波形动画
                HStack(spacing: 6) {
                    ForEach(0..<5, id: \.self) { index in
                        Circle()
                            .fill(Color(hex: "C4935A"))
                            .frame(width: 8, height: 8)
                            .scaleEffect(animationPhase % 5 == index ? 1.4 : 0.8)
                            .animation(.easeInOut(duration: 0.3), value: animationPhase)
                    }
                }

                Text("AI 正在分析中...")
                    .font(.system(size: 14))
                    .foregroundColor(Color(hex: "C4935A"))
            }
            .padding(.bottom, 60)
        }
        .frame(maxWidth: .infinity, maxHeight: .infinity)
        .background(Color(hex: "F5F4F1"))
        .onAppear {
            // 启动波形动画
            Timer.scheduledTimer(withTimeInterval: 0.4, repeats: true) { _ in
                animationPhase += 1
            }

            // 延迟显示金句
            DispatchQueue.main.asyncAfter(deadline: .now() + 0.5) {
                withAnimation(.easeIn(duration: 0.5)) {
                    showQuote = true
                }
            }

            // 启动金句切换 Timer（每6秒切换）
            quoteTimer = Timer.scheduledTimer(withTimeInterval: 6.0, repeats: true) { _ in
                // 先隐藏当前金句
                withAnimation(.easeOut(duration: 0.3)) {
                    showQuote = false
                }
                // 切换金句后重新显示
                DispatchQueue.main.asyncAfter(deadline: .now() + 0.4) {
                    currentQuote = QuoteLibrary.randomQuote()
                    withAnimation(.easeIn(duration: 0.5)) {
                        showQuote = true
                    }
                }
            }
        }
        .onDisappear {
            // 重要：视图消失时取消 Timer
            quoteTimer?.invalidate()
            quoteTimer = nil
        }
    }

    // 金句卡片
    private var quoteCard: some View {
        VStack(spacing: 16) {
            Text(currentQuote.text)
                .font(.system(size: 18, weight: .medium))
                .foregroundColor(Color(hex: "1A1918"))
                .multilineTextAlignment(.center)
                .lineSpacing(8)
                .padding(.horizontal, 32)

            Text("— \(currentQuote.author)")
                .font(.system(size: 14))
                .foregroundColor(Color(hex: "9C9B99"))
        }
        .padding(32)
        .frame(maxWidth: 320)
        .background(
            RoundedRectangle(cornerRadius: 20)
                .fill(Color.white)
        )
        .shadow(color: Color.black.opacity(0.08), radius: 16, y: 6)
    }
}

#Preview {
    ProcessingOverlayView()
}