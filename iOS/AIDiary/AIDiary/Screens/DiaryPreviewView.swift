import SwiftUI
import CoreLocation

struct DiaryPreviewView: View {
    let diary: Diary

    @Environment(\.dismiss) private var dismiss
    @State private var activeTab: Tab = .ai
    @State private var isSaving = false
    @State private var isEditing = false
    @State private var editedText: String = ""

    enum Tab {
        case ai, raw
    }

    var body: some View {
        VStack(spacing: 0) {
            statusBarPlaceholder

            navBar

            ScrollView {
                VStack(spacing: 16) {
                    tabSelector

                    textCard

                    analysisSection
                }
                .padding(.horizontal, 16)
                .padding(.bottom, 100)
            }

            saveButton
        }
        .background(Color(hex: "F5F4F1"))
        .onAppear {
            editedText = diary.cleanedText ?? diary.rawText
            fetchWeatherAsync()
        }
    }

    private var statusBarPlaceholder: some View {
        Color.clear.frame(height: 62)
    }

    private var navBar: some View {
        HStack {
            Button {
                dismiss()
            } label: {
                Text("< 重新录制")
                    .font(.system(size: 15))
                    .foregroundColor(Color(hex: "C4935A"))
            }

            Spacer()
        }
        .padding(.horizontal, 24)
        .frame(height: 44)
    }
    
    private var tabSelector: some View {
        HStack(spacing: 4) {
            Button {
                activeTab = .ai
            } label: {
                Text("AI 优化")
                    .font(.system(size: 14))
                    .foregroundColor(activeTab == .ai ? .white : Color(hex: "6D6C6A"))
                    .frame(maxWidth: .infinity)
                    .padding(.vertical, 10)
                    .background(
                        RoundedRectangle(cornerRadius: 8)
                            .fill(activeTab == .ai ? Color(hex: "C4935A") : Color.clear)
                    )
            }
            
            Button {
                activeTab = .raw
            } label: {
                Text("原始转写")
                    .font(.system(size: 14))
                    .foregroundColor(activeTab == .raw ? .white : Color(hex: "6D6C6A"))
                    .frame(maxWidth: .infinity)
                    .padding(.vertical, 10)
                    .background(
                        RoundedRectangle(cornerRadius: 8)
                            .fill(activeTab == .raw ? Color(hex: "C4935A") : Color.clear)
                    )
            }
        }
        .padding(4)
        .background(Color.white)
        .cornerRadius(12)
        .overlay(
            RoundedRectangle(cornerRadius: 12)
                .stroke(Color(hex: "E5E4E1"), lineWidth: 1)
        )
        .padding(.top, 8)
    }
    
    private var textCard: some View {
        VStack(alignment: .leading, spacing: 8) {
            HStack {
                Text(isEditing ? "编辑文本" : (activeTab == .ai ? "AI 优化" : "原始转写"))
                    .font(.system(size: 16, weight: .semibold))
                    .foregroundColor(Color(hex: "1A1918"))
                Spacer()
                if !isEditing {
                    Button {
                        withAnimation {
                            isEditing = true
                            editedText = activeTab == .ai ? (diary.cleanedText ?? diary.rawText) : diary.rawText
                        }
                    } label: {
                        Text("编辑")
                            .font(.system(size: 12))
                            .foregroundColor(Color(hex: "C4935A"))
                    }
                }
            }
            
            if isEditing {
                TextEditor(text: $editedText)
                    .font(.system(size: 15))
                    .foregroundColor(Color(hex: "1A1918"))
                    .frame(minHeight: 150)
                    .padding(8)
                    .background(Color(hex: "FAFAFA"))
                    .cornerRadius(8)
                    .overlay(
                        RoundedRectangle(cornerRadius: 8)
                            .stroke(Color(hex: "E5E4E1"), lineWidth: 1)
                    )
                
                HStack {
                    Button {
                        withAnimation {
                            isEditing = false
                            editedText = diary.cleanedText ?? diary.rawText
                        }
                    } label: {
                        Text("取消")
                            .font(.system(size: 14))
                            .foregroundColor(Color(hex: "6D6C6A"))
                            .frame(maxWidth: .infinity)
                            .padding(.vertical, 10)
                            .background(Color(hex: "E5E4E1"))
                            .cornerRadius(8)
                    }
                    
                    Button {
                        withAnimation {
                            isEditing = false
                        }
                    } label: {
                        Text("完成")
                            .font(.system(size: 14))
                            .foregroundColor(.white)
                            .frame(maxWidth: .infinity)
                            .padding(.vertical, 10)
                            .background(Color(hex: "C4935A"))
                            .cornerRadius(8)
                    }
                }
            } else {
                Text(activeTab == .ai ? (diary.cleanedText ?? diary.rawText) : diary.rawText)
                    .font(.system(size: 16, design: .serif))
                    .foregroundColor(Color(hex: "1A1918"))
                    .lineSpacing(8)
            }
            
            Text("共 \(diary.wordCount) 字")
                .font(.system(size: 12))
                .foregroundColor(Color(hex: "9C9B99"))
        }
        .padding(16)
        .frame(maxWidth: .infinity, alignment: .leading)
        .background(Color.white)
        .cornerRadius(16)
        .shadow(color: Color.black.opacity(0.08), radius: 12, y: 2)
    }
    
    private var analysisSection: some View {
        VStack(alignment: .leading, spacing: 12) {
            Text("AI 分析")
                .font(.system(size: 18, weight: .semibold))
                .foregroundColor(Color(hex: "1A1918"))
            
            emotionCard
            
            if let topics = diary.topics, !topics.isEmpty {
                topicsCard(topics)
            }
            
            if let events = diary.keyEvents, !events.isEmpty {
                eventsCard(events)
            }
        }
        .padding(.top, 24)
    }
    
    private var emotionCard: some View {
        HStack(spacing: 12) {
            Text("😊")
                .font(.system(size: 24))

            VStack(alignment: .leading, spacing: 2) {
                Text("情绪分析")
                    .font(.system(size: 12))
                    .foregroundColor(Color(hex: "9C9B99"))

                HStack(spacing: 8) {
                    Text(diary.emotion ?? "平静")
                        .font(.system(size: 14))
                        .foregroundColor(Color(hex: "1A1918"))

                    // 能量值展示
                    let energy = diary.effectiveEnergy
                    Text(energy >= 0 ? String(format: "+%.1f", energy) : String(format: "%.1f", energy))
                        .font(.system(size: 14))
                        .foregroundColor(energyColor(energy))

                    // 强度展示
                    if let intensity = diary.emotionIntensity {
                        Text("强度\(String(format: "%.0f", intensity))/10")
                            .font(.system(size: 12))
                            .foregroundColor(Color(hex: "9C9B99"))
                    }
                }
            }

            Spacer()
        }
        .padding(16)
        .background(Color.white)
        .cornerRadius(12)
        .shadow(color: Color.black.opacity(0.08), radius: 8, y: 2)
    }

    /// 能量值颜色
    private func energyColor(_ energy: Double) -> Color {
        if energy >= 7 {
            return Color(hex: "2D7A4A")
        } else if energy >= 3 {
            return Color(hex: "3D8A5A")
        } else if energy >= 0 {
            return Color(hex: "C8F0D8")
        } else if energy >= -3 {
            return Color(hex: "F0E0D0")
        } else if energy >= -7 {
            return Color(hex: "D89575")
        } else {
            return Color(hex: "D08068")
        }
    }
    
    private func topicsCard(_ topics: [String]) -> some View {
        HStack(spacing: 12) {
            Text("🏷️")
                .font(.system(size: 24))
            
            VStack(alignment: .leading, spacing: 2) {
                Text("主题标签")
                    .font(.system(size: 12))
                    .foregroundColor(Color(hex: "9C9B99"))
                
                Text(topics.map { "#\($0)" }.joined(separator: " "))
                    .font(.system(size: 14))
                    .foregroundColor(Color(hex: "1A1918"))
            }
            
            Spacer()
        }
        .padding(16)
        .background(Color.white)
        .cornerRadius(12)
        .shadow(color: Color.black.opacity(0.08), radius: 8, y: 2)
    }
    
    private func eventsCard(_ events: [String]) -> some View {
        HStack(spacing: 12) {
            Text("⭐")
                .font(.system(size: 24))
            
            VStack(alignment: .leading, spacing: 2) {
                Text("关键事件")
                    .font(.system(size: 12))
                    .foregroundColor(Color(hex: "9C9B99"))
                
                Text(events.first ?? "")
                    .font(.system(size: 14))
                    .foregroundColor(Color(hex: "1A1918"))
            }
            
            Spacer()
        }
        .padding(16)
        .background(Color.white)
        .cornerRadius(12)
        .shadow(color: Color.black.opacity(0.08), radius: 8, y: 2)
    }
    
    private var saveButton: some View {
        VStack(spacing: 8) {
            Button {
                confirmSave()
            } label: {
                if isSaving {
                    ProgressView()
                        .tint(.white)
                } else {
                    Text("确认保存")
                        .font(.system(size: 16, weight: .semibold))
                        .foregroundColor(.white)
                        .frame(maxWidth: .infinity)
                        .padding(.vertical, 16)
                        .background(Color(hex: "C4935A"))
                        .cornerRadius(12)
                }
            }
            .disabled(isSaving)

            Text("已自动保存，编辑后点确认更新")
                .font(.system(size: 12))
                .foregroundColor(Color(hex: "9C9B99"))
        }
        .padding(16)
        .padding(.bottom, 40)
    }

    private func confirmSave() {
        // 立即发送通知关闭录音页面，回到时间轴
        NotificationCenter.default.post(name: .diaryConfirmSave, object: nil)
        dismiss()

        // 后台异步更新
        Task {
            let finalText = editedText.isEmpty ? (diary.cleanedText ?? diary.rawText) : editedText

            // 判断是否真正编辑了内容
            let originalText = diary.cleanedText ?? diary.rawText
            if finalText != originalText {
                do {
                    // 1. 先调用后端 API 更新
                    let updatedDiary = try await APIService.shared.updateDiary(id: diary.id, cleanedText: finalText)

                    // 2. 更新本地缓存
                    await CacheService.shared.saveDiary(updatedDiary)

                    // 3. 发送通知刷新时间轴
                    await MainActor.run {
                        NotificationCenter.default.post(name: .diaryDidUpdate, object: nil)
                    }
                } catch {
                    // 更新失败，静默处理
                }
            }
        }
    }

    // 异步获取天气（不阻塞用户流程）
    private func fetchWeatherAsync() {
        Task(priority: .background) {
            // 1. 获取位置
            let location = await withCheckedContinuation { continuation in
                LocationService.shared.getCurrentLocation { loc in
                    continuation.resume(returning: loc)
                }
            }

            guard let loc = location else { return }

            // 2. 获取天气
            let weather = await withCheckedContinuation { continuation in
                WeatherService.shared.getWeather(location: loc) { w in
                    continuation.resume(returning: w)
                }
            }

            guard let w = weather else { return }

            // 3. 获取城市名，创建 Weather 对象并更新到后端
            let city = LocationService.shared.currentCity ?? "未知"
            let weatherWithCity = Weather(
                temperature: w.temperature,
                weather: w.weather,
                weatherIcon: w.weatherIcon,
                location: city
            )

            do {
                try await APIService.shared.updateWeather(diaryId: diary.id, weather: weatherWithCity)
            } catch {
                // 静默失败，不影响用户体验
            }
        }
    }
}

#Preview {
    DiaryPreviewView(
        diary: Diary(
            id: 1,
            rawText: "今天去公园散步了，天气很好",
            cleanedText: "今天去公园散步，天气晴朗",
            emotion: "高兴",
            emotionScore: 7.5,
            emotionEnergy: 6.0,
            emotionIntensity: 6.0,
            emotionKeywords: ["开心"],
            secondaryEmotions: ["期待"],
            emotionDimension: "positive",
            emotionConfidence: 0.85,
            topics: ["散步", "天气"],
            keyEvents: ["公园散步"],
            recordingDuration: 60,
            wordCount: 20,
            weather: Weather(temperature: 26, weather: "晴", weatherIcon: "100", location: "北京"),
            createdAt: Date(),
            updatedAt: Date()
        )
    )
}