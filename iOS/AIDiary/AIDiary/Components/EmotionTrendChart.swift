import SwiftUI
import Charts

struct EmotionTrendChart: View {
    let data: [EmotionTrendDataPoint]

    var body: some View {
        VStack(alignment: .leading, spacing: 8) {
            Text("情绪能量趋势")
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
            // 零线（参考线）
            RuleMark(y: .value("零线", 0))
                .foregroundStyle(Color(hex: "E5E4E1"))
                .lineStyle(StrokeStyle(lineWidth: 1))

            // 正值区域（绿色）
            if item.energy >= 0 {
                AreaMark(
                    x: .value("日期", item.date, unit: .day),
                    yStart: .value("起点", 0),
                    yEnd: .value("能量", item.energy)
                )
                .foregroundStyle(
                    .linearGradient(
                        colors: [Color(hex: "3D8A5A").opacity(0.3), Color(hex: "3D8A5A").opacity(0.05)],
                        startPoint: .top,
                        endPoint: .bottom
                    )
                )
                .interpolationMethod(.catmullRom)
            }

            // 负值区域（橙红色）
            if item.energy < 0 {
                AreaMark(
                    x: .value("日期", item.date, unit: .day),
                    yStart: .value("起点", 0),
                    yEnd: .value("能量", item.energy)
                )
                .foregroundStyle(
                    .linearGradient(
                        colors: [Color(hex: "D89575").opacity(0.3), Color(hex: "D89575").opacity(0.05)],
                        startPoint: .top,
                        endPoint: .bottom
                    )
                )
                .interpolationMethod(.catmullRom)
            }

            // 折线
            LineMark(
                x: .value("日期", item.date, unit: .day),
                y: .value("能量", item.energy)
            )
            .foregroundStyle(item.energy >= 0 ? Color(hex: "3D8A5A") : Color(hex: "D89575"))
            .interpolationMethod(.catmullRom)

            // 数据点
            PointMark(
                x: .value("日期", item.date, unit: .day),
                y: .value("能量", item.energy)
            )
            .foregroundStyle(item.energy >= 0 ? Color(hex: "3D8A5A") : Color(hex: "D89575"))
            .annotation(position: .top, alignment: .center) {
                Text(energyLabel(item.energy))
                    .font(.system(size: 10))
                    .foregroundColor(item.energy >= 0 ? Color(hex: "3D8A5A") : Color(hex: "D89575"))
            }
        }
        .frame(height: 200)
        .padding(.horizontal, 16)
        .chartYAxis {
            AxisMarks(position: .leading, values: [-10, -5, 0, 5, 10])
        }
        .chartYScale(domain: -10...10)
        .chartXAxis {
            AxisMarks(values: .stride(by: .day, count: max(1, data.count / 5))) { value in
                AxisGridLine(stroke: StrokeStyle(lineWidth: 0.5))
                    .foregroundStyle(Color(hex: "E5E4E1"))
                if value.as(Date.self) != nil {
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

    private func energyLabel(_ energy: Double) -> String {
        if energy >= 0 {
            return String(format: "+%.1f", energy)
        } else {
            return String(format: "%.1f", energy)
        }
    }
}

struct EmotionTrendDataPoint: Identifiable {
    let id = UUID()
    let date: Date
    let energy: Double  // 改为 energy
    let intensity: Double?  // 新增强度
    let diaryCount: Int
}

#Preview {
    EmotionTrendChart(
        data: [
            EmotionTrendDataPoint(date: Date().addingTimeInterval(-86400 * 6), energy: 3.5, intensity: 5, diaryCount: 1),
            EmotionTrendDataPoint(date: Date().addingTimeInterval(-86400 * 5), energy: 6.2, intensity: 7, diaryCount: 2),
            EmotionTrendDataPoint(date: Date().addingTimeInterval(-86400 * 4), energy: -2.8, intensity: 6, diaryCount: 1),
            EmotionTrendDataPoint(date: Date().addingTimeInterval(-86400 * 3), energy: 5.0, intensity: 6, diaryCount: 3),
            EmotionTrendDataPoint(date: Date().addingTimeInterval(-86400 * 2), energy: -4.5, intensity: 7, diaryCount: 2),
            EmotionTrendDataPoint(date: Date().addingTimeInterval(-86400 * 1), energy: 2.8, intensity: 4, diaryCount: 1),
            EmotionTrendDataPoint(date: Date(), energy: 6.2, intensity: 8, diaryCount: 4)
        ]
    )
}