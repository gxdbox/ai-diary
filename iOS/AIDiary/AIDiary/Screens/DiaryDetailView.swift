import SwiftUI

struct DiaryDetailView: View {
    let diary: Diary  // 传入的原始日记

    @Environment(\.dismiss) private var dismiss
    @State private var showDeleteConfirm = false
    @State private var isDeleting = false
    @State private var showOriginalText = false
    @State private var isEditing = false
    @State private var editedText: String = ""
    @State private var isSavingEdit = false
    @State private var showCopySuccess = false
    @State private var currentDiary: Diary?  // 当前显示的日记（可能被更新）
    
    var body: some View {
        ScrollView {
            VStack(spacing: 16) {
                headerCard
                
                textCard
                
                aiPanel
            }
            .padding(.horizontal, 16)
            .padding(.bottom, 40)
        }
        .background(Color(hex: "F5F4F1"))
        .navigationTitle("日记详情")
        .navigationBarTitleDisplayMode(.inline)
        .navigationBarBackButtonHidden(true)
        .onAppear {
            currentDiary = diary
        }
        .toolbar {
            ToolbarItem(placement: .navigationBarLeading) {
                Button {
                    dismiss()
                } label: {
                    Image(systemName: "chevron.left")
                        .font(.system(size: 20, weight: .medium))
                        .foregroundColor(Color(hex: "1A1918"))
                }
            }
            ToolbarItem(placement: .navigationBarTrailing) {
                HStack(spacing: 16) {
                    Button {
                        copyDiary()
                    } label: {
                        Image(systemName: "doc.on.doc")
                            .font(.system(size: 18))
                            .foregroundColor(Color(hex: "C4935A"))
                    }

                    Button {
                        showDeleteConfirm = true
                    } label: {
                        if isDeleting {
                            ProgressView()
                                .tint(Color(hex: "1A1918"))
                        } else {
                            Image(systemName: "trash")
                                .font(.system(size: 18))
                                .foregroundColor(Color(hex: "D08068"))
                        }
                    }
                }
            }
        }
        .confirmationDialog("确定删除这篇日记吗？", isPresented: $showDeleteConfirm) {
            Button("删除", role: .destructive) {
                deleteDiary()
            }
            Button("取消", role: .cancel) {}
        } message: {
            Text("此操作不可撤销")
        }
        .overlay(
            Group {
                if showCopySuccess {
                    VStack {
                        Spacer()
                        HStack {
                            Spacer()
                            Text("已复制到剪贴板")
                                .font(.system(size: 14))
                                .foregroundColor(.white)
                                .padding(.horizontal, 16)
                                .padding(.vertical, 10)
                                .background(Color(hex: "3D8A5A"))
                                .cornerRadius(8)
                            Spacer()
                        }
                        .padding(.bottom, 100)
                    }
                    .transition(.opacity)
                    .onAppear {
                        DispatchQueue.main.asyncAfter(deadline: .now() + 1.5) {
                            withAnimation {
                                showCopySuccess = false
                            }
                        }
                    }
                }
            }
        )
    }
    
    private var displayDiary: Diary {
        currentDiary ?? diary
    }

    private var headerCard: some View {
        VStack(alignment: .leading, spacing: 12) {
            // 天气和日期
            if let weather = displayDiary.weather {
                HStack(spacing: 8) {
                    Text(weather.emoji)
                        .font(.system(size: 18))
                    Text("\(weather.location) · \(weather.temperature)°C \(weather.weather)")
                        .font(.system(size: 14))
                        .foregroundColor(Color(hex: "6D6C6A"))
                }
            }

            Text(displayDiary.createdAt, style: .date)
                .font(.system(size: 20, weight: .semibold))
                .foregroundColor(Color(hex: "1A1918"))

            HStack(spacing: 8) {
                if let duration = displayDiary.recordingDuration {
                    let minutes = duration / 60
                    let seconds = duration % 60
                    Text("录音 \(minutes)分\(seconds)秒")
                        .font(.system(size: 14))
                        .foregroundColor(Color(hex: "6D6C6A"))
                }

                Text("·")
                    .font(.system(size: 14))
                    .foregroundColor(Color(hex: "6D6C6A"))

                Text("\(displayDiary.wordCount)字")
                    .font(.system(size: 14))
                    .foregroundColor(Color(hex: "6D6C6A"))
            }

            if let emotion = displayDiary.emotion {
                VStack(alignment: .leading, spacing: 8) {
                    // 主要情绪
                    HStack(spacing: 8) {
                        Text(emotionEmoji)
                            .font(.system(size: 20))
                        Text(emotion)
                            .font(.system(size: 16, weight: .medium))
                            .foregroundColor(Color(hex: "1A1918"))

                        if let score = displayDiary.emotionScore {
                            Text("\(String(format: "%.1f", score))/10")
                                .font(.system(size: 14))
                                .foregroundColor(emotionDimensionColor)
                        }

                        // 情绪维度标签
                        if let dimension = displayDiary.emotionDimension {
                            Text(dimensionLabel(dimension))
                                .font(.system(size: 11))
                                .foregroundColor(.white)
                                .padding(.horizontal, 6)
                                .padding(.vertical, 2)
                                .background(emotionDimensionColor)
                                .cornerRadius(4)
                        }
                    }

                    // 次要情绪
                    if let secondary = displayDiary.secondaryEmotions, !secondary.isEmpty {
                        HStack(spacing: 6) {
                            Text("伴随:")
                                .font(.system(size: 12))
                                .foregroundColor(Color(hex: "9C9B99"))
                            ForEach(secondary, id: \.self) { emo in
                                Text(emo)
                                    .font(.system(size: 12))
                                    .foregroundColor(Color(hex: "6D6C6A"))
                                    .padding(.horizontal, 8)
                                    .padding(.vertical, 4)
                                    .background(Color(hex: "F0EFEC"))
                                    .cornerRadius(8)
                            }
                        }
                    }

                    // 信心度
                    if let confidence = displayDiary.emotionConfidence, confidence < 0.7 {
                        Text("情绪识别信心度较低")
                            .font(.system(size: 11))
                            .foregroundColor(Color(hex: "D89575"))
                    }
                }
            }
        }
        .padding(16)
        .frame(maxWidth: .infinity, alignment: .leading)
        .background(Color.white)
        .cornerRadius(16)
        .shadow(color: Color.black.opacity(0.08), radius: 12, y: 2)
    }
    
    private var textCard: some View {
        VStack(alignment: .leading, spacing: 8) {
            HStack {
                Text(isEditing ? "编辑中" : (showOriginalText ? "原始转写" : "AI 优化"))
                    .font(.system(size: 16, weight: .semibold))
                    .foregroundColor(Color(hex: "1A1918"))
                Spacer()
                if !isEditing {
                    HStack(spacing: 8) {
                        if displayDiary.rawText != displayDiary.cleanedText {
                            Button {
                                withAnimation {
                                    showOriginalText.toggle()
                                }
                            } label: {
                                Text(showOriginalText ? "查看优化" : "查看原文")
                                    .font(.system(size: 12))
                                    .foregroundColor(Color(hex: "C4935A"))
                            }
                        }

                        Button {
                            withAnimation {
                                isEditing = true
                                editedText = displayDiary.cleanedText ?? displayDiary.rawText
                            }
                        } label: {
                            Text("编辑")
                                .font(.system(size: 12))
                                .foregroundColor(Color(hex: "C4935A"))
                        }
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
                
                HStack(spacing: 8) {
                    Button {
                        withAnimation {
                            isEditing = false
                            editedText = displayDiary.cleanedText ?? displayDiary.rawText
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
                        saveEdit()
                    } label: {
                        if isSavingEdit {
                            ProgressView()
                                .tint(.white)
                        } else {
                            Text("保存")
                                .font(.system(size: 14))
                                .foregroundColor(.white)
                        }
                    }
                    .disabled(isSavingEdit)
                    .frame(maxWidth: .infinity)
                    .padding(.vertical, 10)
                    .background(isSavingEdit ? Color.gray : Color(hex: "C4935A"))
                    .cornerRadius(8)
                }
            } else {
                Text(showOriginalText && displayDiary.cleanedText != nil ? displayDiary.rawText : (displayDiary.cleanedText ?? displayDiary.rawText))
                    .font(.system(size: 15))
                    .foregroundColor(Color(hex: "1A1918"))
                    .lineSpacing(11)
            }
        }
        .padding(16)
        .frame(maxWidth: .infinity, alignment: .leading)
        .background(Color.white)
        .cornerRadius(16)
        .shadow(color: Color.black.opacity(0.08), radius: 12, y: 2)
    }
    
    private var aiPanel: some View {
        VStack(alignment: .leading, spacing: 16) {
            HStack {
                Text("AI 分析")
                    .font(.system(size: 16, weight: .semibold))
                    .foregroundColor(Color(hex: "1A1918"))
                Spacer()
                Text("▼")
                    .font(.system(size: 12))
                    .foregroundColor(Color(hex: "9C9B99"))
            }
            
            if let topics = displayDiary.topics, !topics.isEmpty {
                topicSection(topics)
            }

            if let events = displayDiary.keyEvents, !events.isEmpty {
                eventSection(events)
            }
        }
        .padding(16)
        .frame(maxWidth: .infinity, alignment: .leading)
        .background(Color.white)
        .cornerRadius(16)
        .shadow(color: Color.black.opacity(0.08), radius: 8, y: 2)
    }
    
    private func topicSection(_ topics: [String]) -> some View {
        VStack(alignment: .leading, spacing: 8) {
            Text("主题标签")
                .font(.system(size: 12))
                .foregroundColor(Color(hex: "9C9B99"))
            
            HStack(spacing: 8) {
                ForEach(topics, id: \.self) { topic in
                    Text("#\(topic)")
                        .font(.system(size: 12))
                        .foregroundColor(Color(hex: "3D8A5A"))
                        .padding(.horizontal, 12)
                        .padding(.vertical, 6)
                        .background(Color(hex: "C8F0D8"))
                        .cornerRadius(12)
                }
            }
        }
    }
    
    private func eventSection(_ events: [String]) -> some View {
        VStack(alignment: .leading, spacing: 8) {
            Text("关键事件")
                .font(.system(size: 12))
                .foregroundColor(Color(hex: "9C9B99"))
            
            ForEach(events, id: \.self) { event in
                HStack(spacing: 8) {
                    Text("⭐")
                        .font(.system(size: 16))
                    Text(event)
                        .font(.system(size: 14))
                        .foregroundColor(Color(hex: "1A1918"))
                }
            }
        }
    }
    
    private var emotionEmoji: String {
        guard let emotion = displayDiary.emotion else { return "😊" }
        switch emotion {
        case "幸福", "快乐", "欣喜", "欢快", "高兴", "满足", "感恩", "自豪", "期待", "激动", "狂喜", "温情", "自信", "欣慰", "无忧无虑":
            return "😊"
        case "悲伤", "忧郁", "悲痛", "惆怅", "失落", "孤独":
            return "😢"
        case "愤怒", "愤恨", "狂怒", "暴躁", "不满":
            return "😠"
        case "焦虑", "担忧", "恐慌", "恐惧", "惧怕", "不安":
            return "😰"
        case "厌倦", "倦怠", "冷漠", "气馁":
            return "😐"
        case "困惑", "茫然", "不知所措":
            return "😕"
        case "羞耻", "内疚", "懊悔", "羞愤":
            return "😳"
        case "震惊", "惊骇", "惊讶":
            return "😲"
        case "怀旧思乡", "思乡", "乡愁":
            return "🥺"
        default:
            return "😊"
        }
    }

    private var emotionDimensionColor: Color {
        guard let dimension = displayDiary.emotionDimension else {
            return Color(hex: "3D8A5A")
        }
        switch dimension {
        case "positive":
            return Color(hex: "3D8A5A")
        case "negative":
            return Color(hex: "D89575")
        case "mixed":
            return Color(hex: "C4935A")
        case "social":
            return Color(hex: "5B9BD5")
        default:
            return Color(hex: "3D8A5A")
        }
    }

    private func dimensionLabel(_ dimension: String) -> String {
        switch dimension {
        case "positive":
            return "积极"
        case "negative":
            return "消极"
        case "mixed":
            return "复杂"
        case "social":
            return "社交"
        default:
            return ""
        }
    }
    
    private func deleteDiary() {
        isDeleting = true
        Task {
            do {
                try await APIService.shared.deleteDiary(id: diary.id)
                await CacheService.shared.deleteDiary(id: diary.id)
                await MainActor.run {
                    NotificationCenter.default.post(name: .diaryDidDelete, object: nil)
                    dismiss()
                }
            } catch {
                await MainActor.run {
                    isDeleting = false
                }
            }
        }
    }
    
    private func saveEdit() {
        isSavingEdit = true
        Task {
            do {
                // 1. 调用后端 API 更新日记
                let updatedDiary = try await APIService.shared.updateDiary(id: diary.id, cleanedText: editedText)

                // 2. 更新本地缓存
                await CacheService.shared.saveDiary(updatedDiary)

                // 3. 更新当前视图显示
                await MainActor.run {
                    currentDiary = updatedDiary
                    isSavingEdit = false
                    isEditing = false
                    NotificationCenter.default.post(name: .diaryDidUpdate, object: nil)
                }
            } catch {
                await MainActor.run {
                    isSavingEdit = false
                    print("更新日记失败：\(error)")
                }
            }
        }
    }

    private func copyDiary() {
        let text = displayDiary.cleanedText ?? displayDiary.rawText
        UIPasteboard.general.string = text
        withAnimation {
            showCopySuccess = true
        }
    }
}

#Preview {
    NavigationStack {
        DiaryDetailView(
            diary: Diary(
                id: 1,
                rawText: "测试日记",
                cleanedText: "这是测试内容",
                emotion: "高兴",
                emotionScore: 7.5,
                emotionKeywords: ["开心"],
                secondaryEmotions: ["期待"],
                emotionDimension: "positive",
                emotionConfidence: 0.85,
                topics: ["工作", "生活"],
                keyEvents: ["完成项目"],
                recordingDuration: 120,
                wordCount: 50,
                createdAt: Date(),
                updatedAt: Date()
            )
        )
    }
}
