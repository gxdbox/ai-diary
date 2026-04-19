import SwiftUI
import SwiftData

struct TimelineView: View {
    @State private var diaries: [Diary] = []
    @State private var isLoading = false
    @State private var stats: Stats?
    @State private var selectedDiary: Diary?
    @State private var showFilterSheet = false
    @State private var filterOptions: FilterOptions?
    @State private var selectedEmotion: String?
    @State private var selectedTopic: String?
    @State private var selectedTimeRange: TimeRange = .all
    @State private var deletingDiaryId: Int? = nil
    @State private var showDeleteConfirm = false
    @State private var showRecordView = false

    enum TimeRange: String, CaseIterable {
        case today = "今天"
        case week = "本周"
        case month = "本月"
        case all = "全部"

        func toDateRange() -> (start: String?, end: String?) {
            let formatter = DateFormatter()
            formatter.dateFormat = "yyyy-MM-dd"
            let today = Date()

            switch self {
            case .today:
                return (formatter.string(from: today), formatter.string(from: today))
            case .week:
                let weekStart = Calendar.current.date(byAdding: .day, value: -7, to: today)!
                return (formatter.string(from: weekStart), formatter.string(from: today))
            case .month:
                let monthStart = Calendar.current.date(byAdding: .day, value: -30, to: today)!
                return (formatter.string(from: monthStart), formatter.string(from: today))
            case .all:
                return (nil, nil)
            }
        }
    }

    var body: some View {
        NavigationStack {
            ZStack(alignment: .bottomTrailing) {
                VStack(spacing: 0) {
                    statusBarPlaceholder

                    header

                    filterButtons

                    if isLoading {
                        loadingView
                    } else if diaries.isEmpty {
                        emptyView
                    } else {
                        diaryList
                    }
                }

                // 悬浮添加按钮
                addButton
            }
            .background(Color(hex: "F5F4F1"))
            .navigationDestination(item: $selectedDiary) { diary in
                DiaryDetailView(diary: diary)
            }
            .onAppear {
                loadData()
                loadFilterOptions()
            }
            .onReceive(NotificationCenter.default.publisher(for: .diaryDidDelete)) { _ in
                loadData()
            }
            .onReceive(NotificationCenter.default.publisher(for: .diaryDidCreate)) { _ in
                loadData()
                loadFilterOptions()
                // 不在这里关闭录音页面，让 RecordView 控制跳转流程
            }
            .onReceive(NotificationCenter.default.publisher(for: .diaryDidUpdate)) { _ in
                loadData()
            }
            .sheet(isPresented: $showFilterSheet) {
                FilterSheet(
                    selectedEmotion: $selectedEmotion,
                    selectedTopic: $selectedTopic,
                    selectedTimeRange: $selectedTimeRange,
                    filterOptions: filterOptions,
                    onApply: {
                        loadData()
                    }
                )
            }
            .sheet(isPresented: $showRecordView) {
                RecordView()
            }
            .alert("确定删除这篇日记吗？", isPresented: $showDeleteConfirm) {
                Button("删除", role: .destructive) {
                    if let diaryId = deletingDiaryId {
                        deleteDiary(id: diaryId)
                    }
                }
                Button("取消", role: .cancel) {
                    deletingDiaryId = nil
                }
            } message: {
                Text("此操作不可撤销")
            }
        }
    }

    private var statusBarPlaceholder: some View {
        Color.clear.frame(height: 62)
    }

    private var addButton: some View {
        Button {
            showRecordView = true
        } label: {
            ZStack {
                Circle()
                    .fill(Color(hex: "C4935A"))
                    .frame(width: 56, height: 56)
                    .shadow(color: Color(hex: "C4935A").opacity(0.3), radius: 8, y: 4)

                Image(systemName: "plus")
                    .font(.system(size: 24, weight: .semibold))
                    .foregroundColor(.white)
            }
        }
        .padding(.trailing, 24)
        .padding(.bottom, 100)
    }

    private var header: some View {
        VStack(alignment: .leading, spacing: 8) {
            Text("松果日记")
                .font(.system(size: 26, weight: .semibold))
                .foregroundColor(Color(hex: "1A1918"))

            HStack(spacing: 16) {
                Text("已记录 \(stats?.totalDiaries ?? diaries.count) 篇")
                    .font(.system(size: 14))
                    .foregroundColor(Color(hex: "6D6C6A"))

                if let streak = stats?.streakDays, streak > 0 {
                    Text("🐿️ 连续 \(streak) 天")
                        .font(.system(size: 14))
                        .foregroundColor(Color(hex: "D89575"))
                }
            }
        }
        .frame(maxWidth: .infinity, alignment: .leading)
        .padding(.horizontal, 24)
        .padding(.bottom, 12)
    }

    private var filterButtons: some View {
        HStack(spacing: 8) {
            FilterChip(
                title: selectedEmotion ?? "情绪",
                isSelected: selectedEmotion != nil,
                icon: "😊"
            ) {
                showFilterSheet = true
            }

            FilterChip(
                title: selectedTopic ?? "主题",
                isSelected: selectedTopic != nil,
                icon: "🏷️"
            ) {
                showFilterSheet = true
            }

            FilterChip(
                title: selectedTimeRange.rawValue,
                isSelected: selectedTimeRange != .all,
                icon: "📅"
            ) {
                showFilterSheet = true
            }

            if selectedEmotion != nil || selectedTopic != nil || selectedTimeRange != .all {
                Button {
                    clearFilters()
                } label: {
                    Text("清除")
                        .font(.system(size: 12))
                        .foregroundColor(Color(hex: "C4935A"))
                }
            }
        }
        .padding(.horizontal, 16)
        .padding(.bottom, 12)
    }

    private var loadingView: some View {
        VStack {
            Spacer()
            ProgressView()
                .tint(Color(hex: "C4935A"))
            Spacer()
        }
    }

    private var emptyView: some View {
        VStack(spacing: 16) {
            Spacer()
            Text("📝")
                .font(.system(size: 48))
            Text("还没有收藏松果")
                .font(.system(size: 18, weight: .semibold))
                .foregroundColor(Color(hex: "1A1918"))
            Text("点击下方按钮开始珍藏记忆")
                .font(.system(size: 14))
                .foregroundColor(Color(hex: "9C9B99"))
            Spacer()
        }
    }

    private var diaryList: some View {
        ScrollView {
            LazyVStack(spacing: 12) {
                ForEach(diaries) { diary in
                    SwipeableDiaryCard(
                        diary: diary,
                        onTap: { selected in
                            selectedDiary = selected
                        },
                        onDelete: {
                            deletingDiaryId = diary.id
                            showDeleteConfirm = true
                        }
                    )
                }
            }
            .padding(.horizontal, 16)
            .padding(.bottom, 100)
        }
        .refreshable {
            await refreshData()
        }
    }

    private func deleteDiary(id: Int) {
        Task {
            do {
                try await APIService.shared.deleteDiary(id: id)
                await CacheService.shared.deleteDiary(id: id)
                await MainActor.run {
                    diaries.removeAll { $0.id == id }
                    deletingDiaryId = nil
                    NotificationCenter.default.post(name: .diaryDidDelete, object: nil)
                }
            } catch {
                print("删除失败: \(error)")
            }
        }
    }

    private func loadData() {
        isLoading = true
        Task {
            do {
                let dateRange = selectedTimeRange.toDateRange()
                let response = try await APIService.shared.fetchDiaries(
                    emotion: selectedEmotion,
                    topic: selectedTopic,
                    startDate: dateRange.start,
                    endDate: dateRange.end
                )
                let statsData = try await APIService.shared.fetchStats()

                var mergedDiaries: [Diary] = []

                if selectedEmotion != nil || selectedTopic != nil || selectedTimeRange != .all {
                    // 有筛选 → 只用网络数据（保证筛选条件匹配）
                    mergedDiaries = response.items
                } else {
                    // 无筛选 → 网络数据优先，保留缓存独有的（离线创建）
                    let cachedDiaries = await CacheService.shared.getAllDiaries()
                    var cachedDict = Dictionary(grouping: cachedDiaries, by: { $0.id })

                    // 网络有的 → 用网络版本（最新数据）
                    for networkDiary in response.items {
                        mergedDiaries.append(networkDiary)
                        cachedDict[networkDiary.id] = nil  // 标记已处理
                    }

                    // 网络没有但缓存有 → 保留（离线创建或未同步）
                    for (_, cachedList) in cachedDict {
                        mergedDiaries.append(contentsOf: cachedList)
                    }

                    // 更新缓存（网络成功后，保持缓存最新）
                    await CacheService.shared.saveDiaries(mergedDiaries)
                }

                mergedDiaries.sort { $0.createdAt > $1.createdAt }

                await MainActor.run {
                    diaries = mergedDiaries
                    stats = statsData
                    isLoading = false
                }
            } catch {
                // 网络失败 → 用缓存兜底
                let cachedDiaries = await CacheService.shared.getAllDiaries()
                let cachedStats = await CacheService.shared.getStats()

                await MainActor.run {
                    diaries = cachedDiaries
                    stats = cachedStats
                    isLoading = false
                    print("网络请求失败，使用缓存数据: \(error)")
                }
            }
        }
    }

    private func loadFilterOptions() {
        Task {
            do {
                let options = try await APIService.shared.fetchFilters()
                await MainActor.run {
                    filterOptions = options
                }
            } catch {
                print("获取筛选选项失败: \(error)")
            }
        }
    }

    private func refreshData() async {
        isLoading = true
        do {
            let dateRange = selectedTimeRange.toDateRange()
            let response = try await APIService.shared.fetchDiaries(
                emotion: selectedEmotion,
                topic: selectedTopic,
                startDate: dateRange.start,
                endDate: dateRange.end
            )
            let statsData = try await APIService.shared.fetchStats()

            var mergedDiaries: [Diary] = []

            if selectedEmotion != nil || selectedTopic != nil || selectedTimeRange != .all {
                // 有筛选 → 只用网络数据（保证筛选条件匹配）
                mergedDiaries = response.items
            } else {
                // 无筛选 → 网络数据优先，保留缓存独有的
                let cachedDiaries = await CacheService.shared.getAllDiaries()
                var cachedDict = Dictionary(grouping: cachedDiaries, by: { $0.id })

                for networkDiary in response.items {
                    mergedDiaries.append(networkDiary)
                    cachedDict[networkDiary.id] = nil
                }

                for (_, cachedList) in cachedDict {
                    mergedDiaries.append(contentsOf: cachedList)
                }

                await CacheService.shared.saveDiaries(mergedDiaries)
            }

            mergedDiaries.sort { $0.createdAt > $1.createdAt }

            await MainActor.run {
                diaries = mergedDiaries
                stats = statsData
                isLoading = false
            }
        } catch {
            await MainActor.run {
                isLoading = false
            }
        }
    }

    private func clearFilters() {
        selectedEmotion = nil
        selectedTopic = nil
        selectedTimeRange = .all
        loadData()
    }
}

struct FilterChip: View {
    let title: String
    let isSelected: Bool
    let icon: String
    let action: () -> Void

    var body: some View {
        Button(action: action) {
            HStack(spacing: 4) {
                Text(icon)
                    .font(.system(size: 12))
                Text(title)
                    .font(.system(size: 12))
                    .foregroundColor(isSelected ? .white : Color(hex: "6D6C6A"))
            }
            .padding(.horizontal, 12)
            .padding(.vertical, 6)
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

struct DiaryCardView: View {
    let diary: Diary
    let onTap: (Diary) -> Void

    private var isToday: Bool {
        Calendar.current.isDateInToday(diary.createdAt)
    }

    var body: some View {
        VStack(alignment: .leading, spacing: 8) {
            Text(diary.cleanedText ?? diary.rawText)
                .font(.system(size: 15))
                .foregroundColor(Color(hex: "1A1918"))
                .lineLimit(2)
                .multilineTextAlignment(.leading)

            HStack {
                if let emotion = diary.emotion {
                    Text(emotion)
                        .font(.system(size: 12))
                        .foregroundColor(Color(hex: "3D8A5A"))
                        .padding(.horizontal, 8)
                        .padding(.vertical, 4)
                        .background(Color(hex: "C8F0D8"))
                        .cornerRadius(8)
                }

                Text(diary.createdAt.formatted(date: .abbreviated, time: .omitted))
                    .font(.system(size: 12))
                    .foregroundColor(Color(hex: "9C9B99"))

                Spacer()

                Text("\(diary.wordCount)字")
                    .font(.system(size: 12))
                    .foregroundColor(Color(hex: "9C9B99"))
            }
        }
        .padding(16)
        .frame(maxWidth: .infinity, alignment: .leading)
        .background(Color.white)
        .cornerRadius(16)
        .overlay(
            RoundedRectangle(cornerRadius: 16)
                .stroke(Color.clear, lineWidth: 0)
        )
        .overlay(
            Group {
                if isToday {
                    RoundedRectangle(cornerRadius: 16)
                        .stroke(
                            LinearGradient(
                                colors: [Color(hex: "C4935A"), Color(hex: "6BB6D6")],
                                startPoint: .topLeading,
                                endPoint: .bottomTrailing
                            ),
                            lineWidth: 2
                        )
                }
            }
        )
        .shadow(color: Color.black.opacity(0.08), radius: 12, y: 2)
        .onTapGesture {
            onTap(diary)
        }
    }
}

// 左滑删除卡片
struct SwipeableDiaryCard: View {
    let diary: Diary
    let onTap: (Diary) -> Void
    let onDelete: () -> Void

    @State private var offset: CGFloat = 0
    @State private var showDeleteButton = false

    private let deleteThreshold: CGFloat = -80

    var body: some View {
        ZStack(alignment: .trailing) {
            // 删除按钮背景
            if showDeleteButton {
                Button {
                    onDelete()
                    withAnimation {
                        offset = 0
                        showDeleteButton = false
                    }
                } label: {
                    VStack {
                        Spacer()
                        HStack {
                            Spacer()
                            VStack(spacing: 4) {
                                Image(systemName: "trash")
                                    .font(.system(size: 20))
                                    .foregroundColor(.white)
                                Text("删除")
                                    .font(.system(size: 12))
                                    .foregroundColor(.white)
                            }
                            .frame(width: 80)
                            .frame(maxHeight: .infinity)
                            .background(Color(hex: "D08068"))
                        }
                        Spacer()
                    }
                }
                .cornerRadius(16, corners: [.topRight, .bottomRight])
            }

            // 卡片内容
            DiaryCardView(diary: diary, onTap: { diary in
                // 点击卡片时隐藏删除按钮
                if showDeleteButton {
                    withAnimation {
                        offset = 0
                        showDeleteButton = false
                    }
                } else {
                    onTap(diary)
                }
            })
                .offset(x: offset)
                .simultaneousGesture(
                    DragGesture()
                        .onChanged { value in
                            // 只允许左滑
                            if value.translation.width < 0 {
                                offset = value.translation.width
                            }
                        }
                        .onEnded { value in
                            let predictedOffset = value.translation.width + value.predictedEndTranslation.width * 0.3

                            if predictedOffset < deleteThreshold {
                                // 滑动足够，显示删除按钮
                                withAnimation(.easeOut) {
                                    offset = -80
                                    showDeleteButton = true
                                }
                            } else {
                                // 回弹
                                withAnimation(.spring()) {
                                    offset = 0
                                    showDeleteButton = false
                                }
                            }
                        }
                )
        }
        .frame(maxWidth: .infinity)
    }
}

// 圆角扩展
extension View {
    func cornerRadius(_ radius: CGFloat, corners: UIRectCorner) -> some View {
        clipShape(RoundedCorner(radius: radius, corners: corners))
    }
}

struct RoundedCorner: Shape {
    var radius: CGFloat = .infinity
    var corners: UIRectCorner = .allCorners

    func path(in rect: CGRect) -> Path {
        let path = UIBezierPath(
            roundedRect: rect,
            byRoundingCorners: corners,
            cornerRadii: CGSize(width: radius, height: radius)
        )
        return Path(path.cgPath)
    }
}

#Preview {
    ContentView()
}