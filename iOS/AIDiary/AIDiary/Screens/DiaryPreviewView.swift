import SwiftUI

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
                    .foregroundColor(Color(hex: "8B7EC8"))
            }
            
            Spacer()

            Button {
                confirmSave()
            } label: {
                Text("确认")
                    .font(.system(size: 15, weight: .semibold))
                    .foregroundColor(Color(hex: "8B7EC8"))
            }
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
                            .fill(activeTab == .ai ? Color(hex: "8B7EC8") : Color.clear)
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
                            .fill(activeTab == .raw ? Color(hex: "8B7EC8") : Color.clear)
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
                            .foregroundColor(Color(hex: "8B7EC8"))
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
                            .background(Color(hex: "8B7EC8"))
                            .cornerRadius(8)
                    }
                }
            } else {
                Text(activeTab == .ai ? (diary.cleanedText ?? diary.rawText) : diary.rawText)
                    .font(.system(size: 15))
                    .foregroundColor(Color(hex: "1A1918"))
                    .lineSpacing(11)
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
                    
                    if let score = diary.emotionScore {
                        Text("\(String(format: "%.1f", score))/10")
                            .font(.system(size: 14))
                            .foregroundColor(Color(hex: "3D8A5A"))
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
                        .background(Color(hex: "8B7EC8"))
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
        // 如果没有编辑，直接关闭
        if editedText.isEmpty || editedText == (diary.cleanedText ?? diary.rawText) {
            dismiss()
            return
        }

        // 有编辑，更新缓存
        isSaving = true
        Task {
            let finalText = editedText

            let updatedDiary = Diary(
                id: diary.id,
                rawText: diary.rawText,
                cleanedText: finalText,
                emotion: diary.emotion,
                emotionScore: diary.emotionScore,
                emotionKeywords: diary.emotionKeywords,
                secondaryEmotions: diary.secondaryEmotions,
                emotionDimension: diary.emotionDimension,
                emotionConfidence: diary.emotionConfidence,
                topics: diary.topics,
                keyEvents: diary.keyEvents,
                recordingDuration: diary.recordingDuration,
                wordCount: finalText.count,
                createdAt: diary.createdAt,
                updatedAt: Date()
            )

            await CacheService.shared.saveDiary(updatedDiary)

            print("编辑后更新日记：ID=\(diary.id), 字数=\(finalText.count)")

            await MainActor.run {
                NotificationCenter.default.post(name: .diaryDidUpdate, object: nil)
                isSaving = false
                dismiss()
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
            emotionKeywords: ["开心"],
            secondaryEmotions: ["期待"],
            emotionDimension: "positive",
            emotionConfidence: 0.85,
            topics: ["散步", "天气"],
            keyEvents: ["公园散步"],
            recordingDuration: 60,
            wordCount: 20,
            createdAt: Date(),
            updatedAt: Date()
        )
    )
}