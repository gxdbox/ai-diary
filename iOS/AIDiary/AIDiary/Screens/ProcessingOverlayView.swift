import SwiftUI
import Combine

/// AI 处理等待界面 - 展示金句让等待更有意义
struct ProcessingOverlayView: View {
    @State private var currentQuote: Quote = QuoteLibrary.randomQuote()
    @State private var showQuote = false
    @State private var waveScale: CGFloat = 1.0

    var body: some View {
        VStack(spacing: 24) {
            // 顶部进度提示
            VStack(spacing: 8) {
                // 简化的动态波形动画
                HStack(spacing: 6) {
                    ForEach(0..<5, id: \.self) { index in
                        Circle()
                            .fill(Color(hex: "8B7EC8"))
                            .frame(width: 10, height: 10)
                            .scaleEffect(waveScale)
                            .animation(
                                Animation.easeInOut(duration: 0.5)
                                    .repeatForever()
                                    .delay(Double(index) * 0.1),
                                value: waveScale
                            )
                    }
                }
                .onAppear {
                    waveScale = 1.3
                }

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
            // 延迟显示金句
            DispatchQueue.main.asyncAfter(deadline: .now() + 1) {
                withAnimation(.easeIn(duration: 0.5)) {
                    showQuote = true
                }
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