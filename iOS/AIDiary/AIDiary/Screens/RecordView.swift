import SwiftUI
import AVFoundation

struct RecordView: View {
    @StateObject private var speechService = SpeechService.shared

    @State private var isProcessing = false
    @State private var showPreview = false
    @State private var currentDiary: Diary?
    @State private var showPermissionAlert = false

    var body: some View {
        VStack(spacing: 0) {
            statusBarPlaceholder

            navBar

            recordSection

            if !speechService.transcribedText.isEmpty {
                transcribeCard
            }

            if speechService.isRecording {
                bottomControls
            }

            if isProcessing {
                processingOverlay
            }
        }
        .sheet(isPresented: $showPreview) {
            if let diary = currentDiary {
                DiaryPreviewView(diary: diary)
            }
        }
        .alert("需要麦克风权限", isPresented: $showPermissionAlert) {
            Button("取消", role: .cancel) {}
            Button("去设置") {
                if let url = URL(string: UIApplication.openSettingsURLString) {
                    UIApplication.shared.open(url)
                }
            }
        } message: {
            Text("请在设置中允许访问麦克风以使用录音功能")
        }
        .onAppear {
            checkPermission()
        }
    }

    private var statusBarPlaceholder: some View {
        Color.clear.frame(height: 62)
    }

    private var navBar: some View {
        Text(Date(), format: .dateTime.month().day().weekday(.wide))
            .font(.system(size: 17, weight: .semibold))
            .foregroundColor(Color(hex: "1A1918"))
            .frame(height: 44)
    }

    private var recordSection: some View {
        VStack(spacing: 24) {
            Spacer()

            // 音量可视化波形
            AudioWaveView(audioLevel: speechService.audioLevel, isRecording: speechService.isRecording)

            // 录音按钮
            Button {
                if speechService.isRecording {
                    if speechService.isPaused {
                        // 继续
                        speechService.resumeRecording(onTextChange: { _ in })
                    } else {
                        // 暂停
                        speechService.pauseRecording()
                    }
                } else {
                    startRecording()
                }
            } label: {
                ZStack {
                    Circle()
                        .fill(speechService.isPaused ? Color(hex: "D89575") : Color(hex: "8B7EC8"))
                        .frame(width: 80, height: 80)

                    if speechService.isRecording && !speechService.isPaused {
                        Circle()
                            .stroke(Color.white.opacity(0.3), lineWidth: 3)
                            .frame(width: 100, height: 100)
                    }

                    Image(systemName: speechService.isPaused ? "play.fill" : (speechService.isRecording ? "pause.fill" : "microphone.fill"))
                        .font(.system(size: 32))
                        .foregroundColor(.white)
                }
            }
            .disabled(isProcessing)

            if speechService.isPaused {
                Text("已暂停")
                    .font(.system(size: 14))
                    .foregroundColor(Color(hex: "D89575"))
            } else if speechService.isRecording {
                Text("正在录音...")
                    .font(.system(size: 14))
                    .foregroundColor(Color(hex: "8B7EC8"))

                Text("已录音 \(speechService.recordingDuration / 60):\(String(format: "%02d", speechService.recordingDuration % 60))")
                    .font(.system(size: 14, design: .monospaced))
                    .foregroundColor(Color(hex: "8B7EC8"))
            } else {
                Text("点击开始录音")
                    .font(.system(size: 14))
                    .foregroundColor(Color(hex: "9C9B99"))

                Text("录音中可暂停、清空或完成")
                    .font(.system(size: 12))
                    .foregroundColor(Color(hex: "9C9B99").opacity(0.7))
            }

            Spacer()
        }
    }

    private var transcribeCard: some View {
        VStack(alignment: .leading, spacing: 12) {
            HStack {
                Text("实时转写")
                    .font(.system(size: 16, weight: .semibold))
                    .foregroundColor(Color(hex: "1A1918"))

                Spacer()

                Text("已记录 \(speechService.transcribedText.count) 字")
                    .font(.system(size: 12))
                    .foregroundColor(Color(hex: "9C9B99"))
            }

            ScrollView {
                Text(speechService.transcribedText)
                    .font(.system(size: 15))
                    .foregroundColor(Color(hex: "6D6C6A"))
            }
            .frame(maxHeight: 200)
        }
        .padding(16)
        .background(Color.white)
        .cornerRadius(16)
        .shadow(color: Color.black.opacity(0.08), radius: 12, y: 2)
        .padding(.horizontal, 16)
    }

    private var bottomControls: some View {
        HStack(spacing: 40) {
            // 清空按钮
            Button {
                speechService.clearText()
            } label: {
                VStack(spacing: 4) {
                    Image(systemName: "trash")
                        .font(.system(size: 20))
                        .foregroundColor(Color(hex: "D08068"))
                    Text("清空")
                        .font(.system(size: 12))
                        .foregroundColor(Color(hex: "D08068"))
                }
                .frame(width: 60, height: 60)
                .background(Color.white)
                .cornerRadius(12)
                .shadow(color: Color.black.opacity(0.08), radius: 8, y: 2)
            }

            // 完成按钮
            Button {
                finishRecording()
            } label: {
                VStack(spacing: 4) {
                    Image(systemName: "checkmark")
                        .font(.system(size: 20, weight: .bold))
                        .foregroundColor(.white)
                    Text("完成")
                        .font(.system(size: 12))
                        .foregroundColor(.white)
                }
                .frame(width: 60, height: 60)
                .background(Color(hex: "8B7EC8"))
                .cornerRadius(12)
                .shadow(color: Color(hex: "8B7EC8").opacity(0.3), radius: 8, y: 2)
            }
        }
        .padding(.horizontal, 60)
        .padding(.bottom, 120)
    }

    private var processingOverlay: some View {
        VStack(spacing: 16) {
            ProgressView()
                .tint(Color(hex: "8B7EC8"))
            Text("AI 正在处理中...")
                .font(.system(size: 16))
                .foregroundColor(Color(hex: "8B7EC8"))
        }
        .frame(maxWidth: .infinity, maxHeight: .infinity)
        .background(Color.white.opacity(0.9))
    }

    private func checkPermission() {
        speechService.requestAuthorization { authorized in
            if !authorized {
                showPermissionAlert = true
            }
        }
    }

    private func startRecording() {
        speechService.requestAuthorization { authorized in
            if authorized {
                speechService.startRecording { text in
                }
            } else {
                showPermissionAlert = true
            }
        }
    }

    private func finishRecording() {
        let text = speechService.stopRecording()

        guard !text.isEmpty else {
            return
        }

        saveDiary(text: text)
    }

    private func saveDiary(text: String) {
        isProcessing = true
        Task {
            do {
                let diary = try await APIService.shared.createDiary(
                    rawText: text,
                    recordingDuration: speechService.recordingDuration
                )
                // 保存到缓存
                await CacheService.shared.saveDiary(diary)
                await MainActor.run {
                    currentDiary = diary
                    isProcessing = false
                    showPreview = true
                    speechService.reset()
                }
            } catch {
                await MainActor.run {
                    isProcessing = false
                }
            }
        }
    }
}

// 音量可视化波形视图
struct AudioWaveView: View {
    let audioLevel: Float
    let isRecording: Bool

    var body: some View {
        ZStack {
            if isRecording {
                ForEach(0..<8, id: \.self) { index in
                    AnimatedWaveBar(
                        audioLevel: audioLevel,
                        angle: Double(index) * 45,
                        index: index
                    )
                }
            }
        }
        .frame(width: 140, height: 140)
    }
}

struct AnimatedWaveBar: View {
    let audioLevel: Float
    let angle: Double
    let index: Int

    @State private var animatedHeight: CGFloat = 10

    var body: some View {
        let baseHeight = CGFloat(audioLevel) * 25 + 10
        let height = animatedHeight

        Rectangle()
            .fill(Color(hex: "8B7EC8").opacity(0.6))
            .frame(width: 4, height: height)
            .cornerRadius(2)
            .offset(
                x: cos(angle * .pi / 180) * 55,
                y: sin(angle * .pi / 180) * 55
            )
            .onAppear {
                // 基于索引的延迟动画
                let delay = Double(index) * 0.1
                withAnimation(.easeInOut(duration: 0.3).delay(delay).repeatForever(autoreverses: true)) {
                    animatedHeight = baseHeight + CGFloat.random(in: -5...5)
                }
            }
            .onChange(of: audioLevel) { _, newLevel in
                let baseHeight = CGFloat(newLevel) * 25 + 10
                animatedHeight = max(baseHeight + CGFloat.random(in: -5...5), 8)
            }
    }
}

#Preview {
    ContentView()
}