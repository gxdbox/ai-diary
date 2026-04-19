import SwiftUI

struct FilterSheet: View {
    @Binding var selectedEmotion: String?
    @Binding var selectedTopic: String?
    @Binding var selectedTimeRange: TimelineView.TimeRange
    let filterOptions: FilterOptions?
    let onApply: () -> Void
    @Environment(\.dismiss) var dismiss

    var body: some View {
        NavigationStack {
            ScrollView {
                VStack(alignment: .leading, spacing: 24) {
                    // 拖拽指示条
                    RoundedRectangle(cornerRadius: 2.5)
                        .fill(Color(hex: "C8C7C5"))
                        .frame(width: 36, height: 5)
                        .frame(maxWidth: .infinity)
                        .padding(.top, 8)

                    // 情绪筛选
                    emotionSection

                    // 主题筛选
                    topicSection

                    // 时间筛选
                    timeRangeSection
                }
                .padding(.horizontal, 16)
            }
            .background(Color(hex: "F5F4F1"))
            .navigationTitle("筛选")
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .navigationBarLeading) {
                    Button("取消") {
                        dismiss()
                    }
                    .foregroundColor(Color(hex: "6D6C6A"))
                }
                ToolbarItem(placement: .navigationBarTrailing) {
                    Button("应用") {
                        onApply()
                        dismiss()
                    }
                    .foregroundColor(Color(hex: "8B7EC8"))
                    .fontWeight(.semibold)
                }
            }
        }
    }

    private var emotionSection: some View {
        VStack(alignment: .leading, spacing: 12) {
            Text("情绪")
                .font(.system(size: 16, weight: .semibold))
                .foregroundColor(Color(hex: "1A1918"))

            if let emotions = filterOptions?.emotions, !emotions.isEmpty {
                LazyVGrid(columns: [GridItem(.adaptive(minimum: 80))], spacing: 8) {
                    ForEach(emotions, id: \.self) { emotion in
                        FilterOptionButton(
                            title: emotion,
                            isSelected: selectedEmotion == emotion
                        ) {
                            if selectedEmotion == emotion {
                                selectedEmotion = nil
                            } else {
                                selectedEmotion = emotion
                            }
                        }
                    }
                }
            } else {
                Text("暂无情绪数据")
                    .font(.system(size: 14))
                    .foregroundColor(Color(hex: "9C9B99"))
            }
        }
    }

    private var topicSection: some View {
        VStack(alignment: .leading, spacing: 12) {
            Text("主题")
                .font(.system(size: 16, weight: .semibold))
                .foregroundColor(Color(hex: "1A1918"))

            if let topics = filterOptions?.topics, !topics.isEmpty {
                LazyVGrid(columns: [GridItem(.adaptive(minimum: 80))], spacing: 8) {
                    ForEach(topics, id: \.self) { topic in
                        FilterOptionButton(
                            title: topic,
                            isSelected: selectedTopic == topic
                        ) {
                            if selectedTopic == topic {
                                selectedTopic = nil
                            } else {
                                selectedTopic = topic
                            }
                        }
                    }
                }
            } else {
                Text("暂无主题数据")
                    .font(.system(size: 14))
                    .foregroundColor(Color(hex: "9C9B99"))
            }
        }
    }

    private var timeRangeSection: some View {
        VStack(alignment: .leading, spacing: 12) {
            Text("时间范围")
                .font(.system(size: 16, weight: .semibold))
                .foregroundColor(Color(hex: "1A1918"))

            HStack(spacing: 8) {
                ForEach(TimelineView.TimeRange.allCases, id: \.self) { range in
                    FilterOptionButton(
                        title: range.rawValue,
                        isSelected: selectedTimeRange == range
                    ) {
                        selectedTimeRange = range
                    }
                }
            }
        }
    }
}

struct FilterOptionButton: View {
    let title: String
    let isSelected: Bool
    let action: () -> Void

    var body: some View {
        Button(action: action) {
            Text(title)
                .font(.system(size: 14))
                .foregroundColor(isSelected ? .white : Color(hex: "6D6C6A"))
                .padding(.horizontal, 16)
                .padding(.vertical, 10)
                .frame(minWidth: 80)
                .background(
                    RoundedRectangle(cornerRadius: 12)
                        .fill(isSelected ? Color(hex: "8B7EC8") : Color.white)
                )
                .overlay(
                    RoundedRectangle(cornerRadius: 12)
                        .stroke(isSelected ? Color(hex: "8B7EC8") : Color(hex: "E5E4E1"), lineWidth: 1)
                )
        }
    }
}

#Preview {
    FilterSheet(
        selectedEmotion: .constant(nil),
        selectedTopic: .constant(nil),
        selectedTimeRange: .constant(.all),
        filterOptions: FilterOptions(emotions: ["快乐", "平静", "焦虑"], topics: ["工作", "生活"]),
        onApply: {}
    )
}