import SwiftUI
import Combine

/// AI 处理等待界面 - 展示金句让等待更有意义
struct ProcessingOverlayView: View {
    @State private var currentQuote: Quote = QuoteLibrary.randomQuote()
    @State private var showQuote = false
    @State private var animationPhase: Int = 0

    let timer = Timer.publish(every: 6, on: .main, in: .common).autoconnect()

    var body: some View {
        VStack(spacing: 24) {
            // 顶部进度提示
            VStack(spacing: 8) {
                // 动态波形动画
                processingWave

                Text("AI 正在分析中...")
                    .font(.system(size: 16))
                    .foregroundColor(Color(hex: "8B7EC8"))
            }

            Spacer()

            // 金句展示区域
            VStack(spacing: 16) {
                if showQuote {
                    quoteCard
                }
            }

            Spacer()

            // 底部提示
            Text("每一次记录，都是与自己的对话")
                .font(.system(size: 12))
                .foregroundColor(Color(hex: "9C9B99"))
        }
        .frame(maxWidth: .infinity, maxHeight: .infinity)
        .background(Color(hex: "F5F4F1"))
        .onAppear {
            // 延迟显示金句，先让用户看到进度
            DispatchQueue.main.asyncAfter(deadline: .now() + 1) {
                withAnimation(.easeIn(duration: 0.5)) {
                    showQuote = true
                }
            }
        }
        .onReceive(timer) { _ in
            // 每6秒更换一条金句
            withAnimation(.easeOut(duration: 0.3)) {
                showQuote = false
            }

            DispatchQueue.main.asyncAfter(deadline: .now() + 0.3) {
                currentQuote = QuoteLibrary.randomQuote()
                withAnimation(.easeIn(duration: 0.5)) {
                    showQuote = true
                }
            }
        }
    }

    // 处理动画波形
    private var processingWave: some View {
        HStack(spacing: 6) {
            ForEach(0..<5, id: \.self) { index in
                Circle()
                    .fill(Color(hex: "8B7EC8"))
                    .frame(width: 8, height: 8)
                    .scaleEffect(animationPhase == index ? 1.3 : 0.7)
                    .animation(
                        Animation.easeInOut(duration: 0.4)
                            .repeatForever()
                            .delay(Double(index) * 0.15),
                        value: animationPhase
                    )
            }
        }
        .onAppear {
            animationPhase = 0
            Timer.scheduledTimer(withTimeInterval: 0.5, repeats: true) { _ in
                animationPhase = (animationPhase + 1) % 5
            }
        }
    }

    // 金句卡片
    private var quoteCard: some View {
        VStack(spacing: 12) {
            Text(currentQuote.text)
                .font(.system(size: 16))
                .foregroundColor(Color(hex: "1A1918"))
                .multilineTextAlignment(.center)
                .lineSpacing(6)
                .padding(.horizontal, 24)

            Text("— \(currentQuote.author)")
                .font(.system(size: 14))
                .foregroundColor(Color(hex: "9C9B99"))
        }
        .padding(24)
        .background(
            RoundedRectangle(cornerRadius: 16)
                .fill(Color.white)
        )
        .shadow(color: Color.black.opacity(0.06), radius: 12, y: 4)
    }
}

#Preview {
    ProcessingOverlayView()
}