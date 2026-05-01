import SwiftUI

struct AnalyticsView: View {
    @State private var timeRange: TimeRange = .sevenDays
    @State private var stats: Stats?
    @State private var insights: [Insight] = []
    @State private var deepInsights: DeepInsightResponse?
    @State private var emotionData: [EmotionTrendDataPoint] = []
    @State private var isLoading = false
    @State private var showDeepInsights = true

    enum TimeRange: String, CaseIterable {
        case sevenDays = "近 7 天"
        case thirtyDays = "近 30 天"
        case ninetyDays = "近 90 天"
        case all = "全部"

        var days: Int {
            switch self {
            case .sevenDays: return 7
            case .thirtyDays: return 30
            case .ninetyDays: return 90
            case .all: return 365
            }
        }
    }

    var body: some View {
        VStack(spacing: 0) {
            statusBarPlaceholder

            header

            if isLoading {
                loadingView
            } else {
                ScrollView {
                    VStack(spacing: 24) {
                        statsRow

                        EmotionTrendChart(data: emotionData)

                        // 深度洞察（新）
                        if showDeepInsights && deepInsights != nil {
                            deepInsightSection
                        }

                        // 原有洞察（保留兼容）
                        if !insights.isEmpty {
                            insightSection
                        }
                    }
                    .padding(.bottom, 100)
                }
            }
        }
        .onAppear {
            loadData()
        }
        .onChange(of: timeRange) { _, _ in
            loadData()
        }
        .background(Color(hex: "F5F4F1"))
    }

    private var statusBarPlaceholder: some View {
        Color.clear.frame(height: 62)
    }

    private var header: some View {
        VStack(alignment: .leading, spacing: 12) {
            Text("我的洞察")
                .font(.system(size: 26, weight: .semibold))
                .foregroundColor(Color(hex: "1A1918"))

            HStack(spacing: 8) {
                ForEach(TimeRange.allCases, id: \.self) { range in
                    TimeRangeButton(
                        range: range,
                        isSelected: timeRange == range
                    ) {
                        timeRange = range
                    }
                }
            }
        }
        .frame(maxWidth: .infinity, alignment: .leading)
        .padding(.horizontal, 24)
        .padding(.bottom, 16)
    }

    private var loadingView: some View {
        VStack {
            Spacer()
            ProgressView()
                .tint(Color(hex: "C4935A"))
            Spacer()
        }
    }

    private var statsRow: some View {
        HStack(spacing: 10) {
            StatCard(icon: "🌰", value: "\(stats?.totalDiaries ?? 0)", label: "松果数")
            StatCard(icon: "🐿️", value: "\(stats?.streakDays ?? 0)", label: "连续收藏")
            StatCard(icon: "📝", value: "\(stats?.totalWords ?? 0)", label: "总字数")
            // 使用能量值展示（正负区分）
            StatCard(
                icon: "⚡",
                value: energyDisplayValue,
                label: "平均能量"
            )
        }
        .padding(.horizontal, 16)
    }

    private var energyDisplayValue: String {
        guard let stats = stats else { return "-" }
        let energy = stats.effectiveEnergy
        if energy >= 0 {
            return String(format: "+%.1f", energy)
        } else {
            return String(format: "%.1f", energy)
        }
    }

    // 深度洞察卡片
    private var deepInsightSection: some View {
        VStack(alignment: .leading, spacing: 16) {
            // 整体摘要
            if let summary = deepInsights?.overallSummary {
                Text(summary)
                    .font(.system(size: 14))
                    .foregroundColor(Color(hex: "6D6C6A"))
                    .padding(.horizontal, 16)
            }

            // 四分类卡片
            ForEach(deepInsights?.categories ?? []) { category in
                DeepInsightCategoryCard(category: category)
            }
        }
    }

    private var insightSection: some View {
        VStack(alignment: .leading, spacing: 12) {
            Text("习惯洞察")
                .font(.system(size: 16, weight: .semibold))
                .foregroundColor(Color(hex: "1A1918"))
                .padding(.horizontal, 16)

            VStack(spacing: 8) {
                ForEach(insights) { insight in
                    InsightRow(insight: insight)
                }
            }
            .padding(16)
            .background(Color.white)
            .cornerRadius(16)
            .shadow(color: Color.black.opacity(0.08), radius: 8, y: 2)
            .padding(.horizontal, 16)
        }
    }

    private func loadData() {
        isLoading = true
        Task {
            do {
                let statsData = try await APIService.shared.fetchStats()
                let insightsData = try await APIService.shared.fetchInsights(days: timeRange.days)
                let trendData = try await APIService.shared.fetchEmotionTrend(days: timeRange.days)

                // 获取深度洞察（90天分析）
                let deepInsightsData = try await APIService.shared.fetchDeepInsights(days: min(timeRange.days, 90))

                let dateFormatter = DateFormatter()
                dateFormatter.dateFormat = "yyyy-MM-dd"
                dateFormatter.locale = Locale(identifier: "en_US_POSIX")

                let points = trendData.compactMap { item -> EmotionTrendDataPoint? in
                    guard let date = dateFormatter.date(from: item.date) else { return nil }
                    return EmotionTrendDataPoint(
                        date: date,
                        energy: item.effectiveEnergy,
                        intensity: item.averageIntensity,
                        diaryCount: item.diaryCount
                    )
                }

                await MainActor.run {
                    stats = statsData
                    insights = insightsData
                    emotionData = points
                    deepInsights = deepInsightsData
                    isLoading = false
                }
            } catch {
                await MainActor.run {
                    isLoading = false
                }
            }
        }
    }
}

// 深度洞察分类卡片
struct DeepInsightCategoryCard: View {
    let category: DeepInsightCategory

    var body: some View {
        VStack(alignment: .leading, spacing: 12) {
            // 分类标题
            HStack(spacing: 8) {
                Text(category.categoryIcon)
                    .font(.system(size: 18))
                Text(category.categoryName)
                    .font(.system(size: 16, weight: .semibold))
                    .foregroundColor(Color(hex: "1A1918"))

                Spacer()

                Text("\(category.insights.count)条")
                    .font(.system(size: 12))
                    .foregroundColor(Color(hex: "9C9B99"))
            }
            .padding(.horizontal, 16)

            // highlight 摘要（如果有）
            if let highlight = category.highlight {
                Text(highlight)
                    .font(.system(size: 13))
                    .foregroundColor(Color(hex: "6D6C6A"))
                    .padding(.horizontal, 16)
                    .padding(.bottom, 4)
            }

            // 洞察列表
            if !category.insights.isEmpty {
                VStack(spacing: 10) {
                    ForEach(category.insights) { insight in
                        DeepInsightRow(insight: insight)
                    }
                }
                .padding(16)
                .background(Color.white)
                .cornerRadius(12)
                .shadow(color: Color.black.opacity(0.05), radius: 6, y: 2)
                .padding(.horizontal, 16)
            }
        }
    }
}

// 深度洞察行
struct DeepInsightRow: View {
    let insight: DeepInsight

    private var severityColor: Color {
        switch insight.severity {
        case "alert": return Color.red.opacity(0.1)
        case "warning": return Color.orange.opacity(0.1)
        default: return Color.clear
        }
    }

    var body: some View {
        VStack(alignment: .leading, spacing: 6) {
            HStack(spacing: 8) {
                Text(insight.icon ?? "💡")
                    .font(.system(size: 16))

                Text(insight.title)
                    .font(.system(size: 14, weight: .medium))
                    .foregroundColor(Color(hex: "1A1918"))

                if insight.severity == "alert" {
                    Image(systemName: "exclamationmark.triangle.fill")
                        .foregroundColor(.red)
                        .font(.system(size: 12))
                }
            }

            Text(insight.insight)
                .font(.system(size: 13))
                .foregroundColor(Color(hex: "3D3C3A"))
                .lineLimit(3)

            // 建议（如果有）
            if let suggestion = insight.suggestion {
                Text(suggestion)
                    .font(.system(size: 12))
                    .foregroundColor(Color(hex: "C4935A"))
                    .padding(.top, 4)
            }
        }
        .padding(12)
        .background(severityColor)
        .cornerRadius(8)
    }
}

struct TimeRangeButton: View {
    let range: AnalyticsView.TimeRange
    let isSelected: Bool
    let action: () -> Void
    
    var body: some View {
        Button(action: action) {
            Text(range.rawValue)
                .font(.system(size: 12))
                .foregroundColor(isSelected ? .white : Color(hex: "6D6C6A"))
                .padding(.horizontal, 14)
                .padding(.vertical, 8)
                .background(
                    RoundedRectangle(cornerRadius: 16)
                        .fill(isSelected ? Color(hex: "C4935A") : Color.white)
                )
                .overlay(
                    RoundedRectangle(cornerRadius: 16)
                        .stroke(isSelected ? Color(hex: "C4935A") : Color(hex: "E5E4E1"), lineWidth: 1)
                )
        }
    }
}

struct StatCard: View {
    let icon: String
    let value: String
    let label: String
    
    var body: some View {
        VStack(spacing: 4) {
            Text(icon)
                .font(.system(size: 20))
            Text(value)
                .font(.system(size: 20, weight: .bold))
                .foregroundColor(Color(hex: "1A1918"))
            Text(label)
                .font(.system(size: 10))
                .foregroundColor(Color(hex: "9C9B99"))
        }
        .frame(maxWidth: .infinity)
        .padding(.vertical, 12)
        .background(Color.white)
        .cornerRadius(12)
        .shadow(color: Color.black.opacity(0.05), radius: 8, y: 2)
    }
}

struct InsightRow: View {
    let insight: Insight
    
    private var icon: String {
        switch insight.type {
        case "emotion": return "😊"
        case "topic": return "🏷️"
        case "habit": return "📊"
        default: return "💡"
        }
    }
    
    var body: some View {
        HStack(spacing: 10) {
            Text(icon)
                .font(.system(size: 18))
            Text(insight.insight)
                .font(.system(size: 13))
                .foregroundColor(Color(hex: "1A1918"))
        }
        .padding(.vertical, 8)
    }
}

#Preview {
    ContentView()
}