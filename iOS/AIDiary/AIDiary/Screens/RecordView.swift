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
            
            Button {
                if speechService.isRecording {
                    stopRecording()
                } else {
                    startRecording()
                }
            } label: {
                ZStack {
                    Circle()
                        .fill(Color(hex: "8B7EC8"))
                        .frame(width: 80, height: 80)
                    
                    if speechService.isRecording {
                        Circle()
                            .stroke(Color.white.opacity(0.3), lineWidth: 3)
                            .frame(width: 100, height: 100)
                    }
                    
                    Text(speechService.isRecording ? "⏹" : "🎤")
                        .font(.system(size: 32))
                        .foregroundColor(.white)
                }
            }
            .disabled(isProcessing)
            
            Text(speechService.isRecording ? "正在录音..." : "点击开始录音")
                .font(.system(size: 14))
                .foregroundColor(Color(hex: "9C9B99"))
            
            if speechService.isRecording {
                Text("已录音 \(speechService.recordingDuration / 60):\(String(format: "%02d", speechService.recordingDuration % 60))")
                    .font(.system(size: 14, design: .monospaced))
                    .foregroundColor(Color(hex: "8B7EC8"))
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
    
    private func stopRecording() {
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

#Preview {
    ContentView()
}