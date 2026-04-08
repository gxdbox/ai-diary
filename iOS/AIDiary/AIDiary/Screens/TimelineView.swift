import SwiftUI
import SwiftData

struct TimelineView: View {
    @State private var diaries: [Diary] = []
    @State private var isLoading = false
    @State private var stats: Stats?
    @State private var selectedDiary: Diary?
    
    var body: some View {
        NavigationStack {
            VStack(spacing: 0) {
                statusBarPlaceholder
                
                header
                
                if isLoading {
                    loadingView
                } else if diaries.isEmpty {
                    emptyView
                } else {
                    diaryList
                }
            }
            .navigationDestination(item: $selectedDiary) { diary in
                DiaryDetailView(diary: diary)
            }
            .onAppear {
                loadData()
            }
            .onReceive(NotificationCenter.default.publisher(for: .diaryDidDelete)) { _ in
                loadData()
            }
            .onReceive(NotificationCenter.default.publisher(for: .diaryDidCreate)) { _ in
                loadData()
            }
            .onReceive(NotificationCenter.default.publisher(for: .diaryDidUpdate)) { _ in
                loadData()
            }
        }
    }
    
    private var statusBarPlaceholder: some View {
        Color.clear.frame(height: 62)
    }
    
    private var header: some View {
        VStack(alignment: .leading, spacing: 8) {
            Text("我的日记")
                .font(.system(size: 26, weight: .semibold))
                .foregroundColor(Color(hex: "1A1918"))
            
            HStack(spacing: 16) {
                Text("已记录 \(stats?.totalDiaries ?? diaries.count) 篇")
                    .font(.system(size: 14))
                    .foregroundColor(Color(hex: "6D6C6A"))
                
                if let streak = stats?.streakDays, streak > 0 {
                    Text("🔥 连续 \(streak) 天")
                        .font(.system(size: 14))
                        .foregroundColor(Color(hex: "D89575"))
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
                .tint(Color(hex: "8B7EC8"))
            Spacer()
        }
    }
    
    private var emptyView: some View {
        VStack(spacing: 16) {
            Spacer()
            Text("📝")
                .font(.system(size: 48))
            Text("还没有日记")
                .font(.system(size: 18, weight: .semibold))
                .foregroundColor(Color(hex: "1A1918"))
            Text("点击下方录音按钮开始记录")
                .font(.system(size: 14))
                .foregroundColor(Color(hex: "9C9B99"))
            Spacer()
        }
    }
    
    private var diaryList: some View {
        ScrollView {
            LazyVStack(spacing: 12) {
                ForEach(diaries) { diary in
                    DiaryCardView(diary: diary, onTap: { selected in
                        selectedDiary = selected
                    })
                }
            }
            .padding(.horizontal, 16)
            .padding(.bottom, 100)
        }
        .refreshable {
            await refreshData()
        }
    }
    
    private func loadData() {
        isLoading = true
        Task {
            do {
                // 先从缓存加载
                let cachedDiaries = await CacheService.shared.getAllDiaries()
                let cachedStats = await CacheService.shared.getStats()
                
                // 从网络更新
                let response = try await APIService.shared.fetchDiaries()
                let statsData = try await APIService.shared.fetchStats()
                
                // 合并数据：缓存中的优先（包含编辑过的）
                // 用缓存中的日记替换网络中的同 ID 日记
                var mergedDiaries: [Diary] = []
                var cachedDict = Dictionary(grouping: cachedDiaries, by: { $0.id })
                
                for networkDiary in response.items {
                    if let cached = cachedDict[networkDiary.id]?.first {
                        // 缓存中有，用缓存的（可能编辑过）
                        mergedDiaries.append(cached)
                        cachedDict[networkDiary.id] = nil
                    } else {
                        // 缓存中没有，用网络的
                        mergedDiaries.append(networkDiary)
                    }
                }
                
                // 添加缓存中独有的日记（网络中没有的）
                for (_, cachedList) in cachedDict {
                    mergedDiaries.append(contentsOf: cachedList)
                }
                
                // 按创建时间排序
                mergedDiaries.sort { $0.createdAt > $1.createdAt }
                
                // 保存到缓存
                await CacheService.shared.saveDiaries(mergedDiaries)
                await CacheService.shared.saveStats(statsData)
                
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
    }
    
    private func refreshData() async {
        isLoading = true
        do {
            // 从网络刷新
            let response = try await APIService.shared.fetchDiaries()
            let statsData = try await APIService.shared.fetchStats()
            
            // 获取缓存数据（包含编辑过的）
            let cachedDiaries = await CacheService.shared.getAllDiaries()
            
            // 合并数据：缓存中的优先
            var mergedDiaries: [Diary] = []
            var cachedDict = Dictionary(grouping: cachedDiaries, by: { $0.id })
            
            for networkDiary in response.items {
                if let cached = cachedDict[networkDiary.id]?.first {
                    mergedDiaries.append(cached)
                    cachedDict[networkDiary.id] = nil
                } else {
                    mergedDiaries.append(networkDiary)
                }
            }
            
            for (_, cachedList) in cachedDict {
                mergedDiaries.append(contentsOf: cachedList)
            }
            
            mergedDiaries.sort { $0.createdAt > $1.createdAt }
            
            // 更新缓存
            await CacheService.shared.saveDiaries(mergedDiaries)
            await CacheService.shared.saveStats(statsData)
            
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
}

struct DiaryCardView: View {
    let diary: Diary
    let onTap: (Diary) -> Void
    
    var body: some View {
        Button {
            onTap(diary)
        } label: {
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
            .shadow(color: Color.black.opacity(0.08), radius: 12, y: 2)
        }
    }
}

#Preview {
    ContentView()
}