import SwiftUI
import Charts

struct EmotionTrendChart: View {
    let data: [EmotionTrendDataPoint]
    
    var body: some View {
        VStack(alignment: .leading, spacing: 8) {
            Text("情绪变化趋势")
                .font(.system(size: 16, weight: .semibold))
                .foregroundColor(Color(hex: "1A1918"))
                .padding(.horizontal, 16)
            
            if data.isEmpty {
                noDataView
            } else {
                chartView
            }
        }
        .padding(.vertical, 16)
    }
    
    private var noDataView: some View {
        VStack(spacing: 8) {
            Text("📈")
                .font(.system(size: 32))
            Text("暂无数据")
                .font(.system(size: 14))
                .foregroundColor(Color(hex: "9C9B99"))
        }
        .frame(maxWidth: .infinity)
        .frame(height: 200)
        .background(Color.white)
        .cornerRadius(12)
        .padding(.horizontal, 16)
    }
    
    private var chartView: some View {
        Chart(data) { item in
            LineMark(
                x: .value("日期", item.date, unit: .day),
                y: .value("情绪分数", item.score)
            )
            .foregroundStyle(Color(hex: "8B7EC8"))
            .interpolationMethod(.catmullRom)
            
            AreaMark(
                x: .value("日期", item.date, unit: .day),
                y: .value("情绪分数", item.score)
            )
            .foregroundStyle(
                .linearGradient(
                    colors: [Color(hex: "8B7EC8").opacity(0.3), Color(hex: "8B7EC8").opacity(0.05)],
                    startPoint: .top,
                    endPoint: .bottom
                )
            )
            .interpolationMethod(.catmullRom)
            
            PointMark(
                x: .value("日期", item.date, unit: .day),
                y: .value("情绪分数", item.score)
            )
            .foregroundStyle(Color(hex: "8B7EC8"))
            .annotation(position: .top, alignment: .center) {
                Text(String(format: "%.1f", item.score))
                    .font(.system(size: 10))
                    .foregroundColor(Color(hex: "8B7EC8"))
            }
        }
        .frame(height: 200)
        .padding(.horizontal, 16)
        .chartYAxis {
            AxisMarks(position: .leading, values: [0, 5, 10])
        }
        .chartYScale(domain: 0...10)
        .chartXAxis {
            AxisMarks(values: .stride(by: .day, count: max(1, data.count / 5))) { value in
                AxisGridLine(stroke: StrokeStyle(lineWidth: 0.5))
                    .foregroundStyle(Color(hex: "E5E4E1"))
                if let date = value.as(Date.self) {
                    AxisValueLabel(format: .dateTime.month().day(), anchor: .top)
                        .font(.system(size: 10))
                        .foregroundStyle(Color(hex: "9C9B99"))
                }
            }
        }
        .background(
            RoundedRectangle(cornerRadius: 12)
                .fill(Color.white)
                .shadow(color: Color.black.opacity(0.05), radius: 8, y: 2)
        )
        .padding(.horizontal, 16)
    }
}

struct EmotionTrendDataPoint: Identifiable {
    let id = UUID()
    let date: Date
    let score: Double
    let diaryCount: Int
}

#Preview {
    EmotionTrendChart(
        data: [
            EmotionTrendDataPoint(date: Date().addingTimeInterval(-86400 * 6), score: 6.5, diaryCount: 1),
            EmotionTrendDataPoint(date: Date().addingTimeInterval(-86400 * 5), score: 7.2, diaryCount: 2),
            EmotionTrendDataPoint(date: Date().addingTimeInterval(-86400 * 4), score: 5.8, diaryCount: 1),
            EmotionTrendDataPoint(date: Date().addingTimeInterval(-86400 * 3), score: 8.0, diaryCount: 3),
            EmotionTrendDataPoint(date: Date().addingTimeInterval(-86400 * 2), score: 7.5, diaryCount: 2),
            EmotionTrendDataPoint(date: Date().addingTimeInterval(-86400 * 1), score: 6.8, diaryCount: 1),
            EmotionTrendDataPoint(date: Date(), score: 8.2, diaryCount: 4)
        ]
    )
}
