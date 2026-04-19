import SwiftUI

struct ContentView: View {
    @State private var selectedTab: Tab = .timeline
    
    enum Tab: String, CaseIterable {
        case timeline = "时间轴"
        case search = "搜索"
        case analytics = "分析"
        case settings = "我的"
    }
    
    var body: some View {
        ZStack {
            Color(hex: "F5F4F1")
                .ignoresSafeArea()
            
            VStack(spacing: 0) {
                selectedTabView
                
                Spacer()
                
                TabBarView(selectedTab: $selectedTab)
            }
        }
    }
    
    @ViewBuilder
    private var selectedTabView: some View {
        switch selectedTab {
        case .timeline:
            TimelineView()
        case .search:
            SearchView()
        case .analytics:
            AnalyticsView()
        case .settings:
            SettingsView()
        }
    }
}

struct TabBarView: View {
    @Binding var selectedTab: ContentView.Tab
    
    private let icons: [ContentView.Tab: String] = [
        .timeline: "📅",
        .search: "🔍",
        .analytics: "📊",
        .settings: "😊"
    ]
    
    var body: some View {
        HStack(spacing: 0) {
            ForEach(ContentView.Tab.allCases, id: \.self) { tab in
                TabBarItem(
                    tab: tab,
                    isSelected: selectedTab == tab,
                    icon: icons[tab] ?? "📌"
                ) {
                    selectedTab = tab
                }
            }
        }
        .padding(4)
        .padding(.horizontal, 21)
        .background(Color.white)
        .cornerRadius(36)
        .overlay(
            RoundedRectangle(cornerRadius: 36)
                .stroke(Color(hex: "E5E4E1"), lineWidth: 1)
        )
        .padding(.horizontal, 21)
        .padding(.bottom, 21)
        .shadow(color: Color.black.opacity(0.1), radius: 12, y: -2)
    }
}

struct TabBarItem: View {
    let tab: ContentView.Tab
    let isSelected: Bool
    let icon: String
    let action: () -> Void
    
    var body: some View {
        Button(action: action) {
            VStack(spacing: 4) {
                Text(icon)
                    .font(.system(size: 18))
                Text(tab.rawValue)
                    .font(.system(size: 10, weight: .medium))
                    .foregroundColor(isSelected ? .white : Color(hex: "A8A7A5"))
            }
            .frame(maxWidth: .infinity)
            .padding(.vertical, 10)
            .background(
                RoundedRectangle(cornerRadius: 26)
                    .fill(isSelected ? Color(hex: "C4935A") : Color.clear)
            )
        }
    }
}

extension Color {
    init(hex: String) {
        let hex = hex.trimmingCharacters(in: CharacterSet.alphanumerics.inverted)
        var int: UInt64 = 0
        Scanner(string: hex).scanHexInt64(&int)
        let a, r, g, b: UInt64
        switch hex.count {
        case 6:
            (a, r, g, b) = (255, int >> 16, int >> 8 & 0xFF, int & 0xFF)
        default:
            (a, r, g, b) = (255, 0, 0, 0)
        }
        self.init(
            .sRGB,
            red: Double(r) / 255,
            green: Double(g) / 255,
            blue: Double(b) / 255,
            opacity: Double(a) / 255
        )
    }
}

#Preview {
    ContentView()
}
