//
//  CharacterDetailView.swift
//  AIDiary
//
//  人物详情和时间轴视图
//

import SwiftUI

struct CharacterDetailView: View {
    let character: Character
    @State private var timelineData: CharacterTimelineResponse?
    @State private var isLoading = false
    @State private var errorMessage: String?
    @Environment(\.dismiss) private var dismiss

    var body: some View {
        NavigationView {
            Group {
                if isLoading {
                    VStack(spacing: 16) {
                        ProgressView()
                            .scaleEffect(1.5)
                        Text("加载人物信息...")
                            .font(.caption)
                            .foregroundColor(.secondary)
                    }

                } else if let error = errorMessage {
                    VStack(spacing: 16) {
                        Image(systemName: "exclamationmark.triangle")
                            .font(.system(size: 48))
                            .foregroundColor(.orange)
                        Text(error)
                            .font(.body)
                            .multilineTextAlignment(.center)
                    }

                } else if let data = timelineData {
                    ScrollView {
                        VStack(alignment: .leading, spacing: 20) {
                            // 人物头部信息
                            CharacterHeader(character: character)

                            Divider()

                            // 基本信息
                            InfoSection(title: "基本信息", content: """
                                首次出现: \(formatDate(character.firstAppearance))
                                最后出现: \(formatDate(character.lastAppearance))
                                出现次数: \(character.appearanceCount) 次
                                """)

                            // 相关日记列表
                            if !data.diaries.isEmpty {
                                DiaryTimelineSection(diaries: data.diaries)
                            } else {
                                EmptyTimelineView()
                            }
                        }
                        .padding()
                    }

                } else {
                    Text("暂无数据")
                        .foregroundColor(.secondary)
                }
            }
            .navigationTitle(character.name)
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .navigationBarTrailing) {
                    Button("关闭") {
                        dismiss()
                    }
                }
            }
            .onAppear {
                loadTimeline()
            }
        }
    }

    private func loadTimeline() {
        isLoading = true
        errorMessage = nil

        Task {
            do {
                timelineData = try await APIService.shared.fetchCharacterTimeline(
                    characterName: character.name,
                    limit: 50
                )
                isLoading = false
            } catch {
                isLoading = false
                errorMessage = "加载失败: \(error.localizedDescription)"
                print("加载人物时间轴失败: \(error)")
            }
        }
    }

    private func formatDate(_ date: Date) -> String {
        let formatter = DateFormatter()
        formatter.dateFormat = "yyyy年MM月dd日"
        return formatter.string(from: date)
    }
}

// MARK: - 人物头部组件
struct CharacterHeader: View {
    let character: Character

    var body: some View {
        HStack(spacing: 16) {
            // 大头像
            Circle()
                .fill(Color(hex: character.avatarColor))
                .frame(width: 80, height: 80)
                .overlay(
                    Text(String(character.name.prefix(1)))
                        .font(.system(size: 36, weight: .bold))
                        .foregroundColor(.white)
                )
                .shadow(color: Color.black.opacity(0.2), radius: 6, x: 0, y: 3)

            VStack(alignment: .leading, spacing: 8) {
                Text(character.name)
                    .font(.title2)
                    .fontWeight(.bold)

                HStack(spacing: 12) {
                    Label("\(character.appearanceCount)", systemImage: "document.fill")
                        .font(.caption)
                        .foregroundColor(.secondary)
                        .padding(.horizontal, 10)
                        .padding(.vertical, 6)
                        .background(Color.gray.opacity(0.15))
                        .cornerRadius(12)
                }
            }

            Spacer()
        }
        .padding(.vertical, 8)
    }
}

// MARK: - 信息区块
struct InfoSection: View {
    let title: String
    let content: String

    var body: some View {
        VStack(alignment: .leading, spacing: 8) {
            Text(title)
                .font(.headline)
                .foregroundColor(.primary)

            Text(content)
                .font(.body)
                .foregroundColor(.secondary)
                .lineSpacing(4)
        }
    }
}

// MARK: - 日记时间轴部分
struct DiaryTimelineSection: View {
    let diaries: [Diary]

    var body: some View {
        VStack(alignment: .leading, spacing: 12) {
            Text("相关日记 (\(diaries.count))")
                .font(.headline)

            ForEach(diaries) { diary in
                DiaryPreviewCard(diary: diary)
            }
        }
    }
}

// MARK: - 日记预览卡片（简化版）
struct DiaryPreviewCard: View {
    let diary: Diary

    var body: some View {
        NavigationLink(destination: DiaryDetailView(diary: diary)) {
            VStack(alignment: .leading, spacing: 8) {
                HStack {
                    Text(formatDate(diary.createdAt))
                        .font(.caption)
                        .foregroundColor(.secondary)

                    Spacer()

                    if let emotion = diary.emotion {
                        Text(emotion)
                            .font(.caption2)
                            .padding(.horizontal, 8)
                            .padding(.vertical, 4)
                            .background(emotionColor(for: emotion).opacity(0.15))
                            .cornerRadius(8)
                    }
                }

                Text(diary.cleanedText ?? diary.rawText)
                    .font(.body)
                    .lineLimit(3)
                    .foregroundColor(.primary)
            }
            .padding()
            .background(Color.white)
            .cornerRadius(12)
            .shadow(color: Color.black.opacity(0.05), radius: 2, x: 0, y: 1)
        }
    }

    private func formatDate(_ date: Date) -> String {
        let formatter = DateFormatter()
        formatter.dateFormat = "yyyy-MM-dd HH:mm"
        return formatter.string(from: date)
    }

    private func emotionColor(for emotion: String) -> Color {
        switch emotion {
        case "快乐", "joy":
            return .yellow
        case "悲伤", "sadness":
            return .blue
        case "愤怒", "anger":
            return .red
        case "焦虑", "anxiety":
            return .orange
        default:
            return .gray
        }
    }
}

// MARK: - 空时间轴视图
struct EmptyTimelineView: View {
    var body: some View {
        VStack(spacing: 12) {
            Image(systemName: "document.text.magnifyingglass")
                .font(.system(size: 48))
                .foregroundColor(.gray.opacity(0.4))

            Text("暂无相关日记")
                .font(.body)
                .foregroundColor(.secondary)
        }
        .padding(.vertical, 40)
    }
}

// MARK: - Preview
struct CharacterDetailView_Previews: PreviewProvider {
    static var previews: some View {
        CharacterDetailView(
            character: Character(
                id: 1,
                name: "张三",
                appearanceCount: 15,
                avatarColor: "#4A90E2",
                firstAppearance: Date(),
                lastAppearance: Date()
            )
        )
    }
}
