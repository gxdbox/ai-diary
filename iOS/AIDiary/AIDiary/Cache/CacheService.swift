import Foundation
import SwiftData

actor CacheService {
    static let shared = CacheService()

    private var modelContainer: ModelContainer?

    private init() {}

    func setup() async {
        do {
            let schema = Schema([
                CachedDiary.self,
                CachedStats.self
            ])
            let configuration = ModelConfiguration(schema: schema, isStoredInMemoryOnly: false)
            modelContainer = try ModelContainer(for: schema, configurations: [configuration])
            print("CacheService 初始化成功")
        } catch {
            print("CacheService 初始化失败：\(error)")
        }
    }

    func saveDiaries(_ diaries: [Diary]) async {
        guard let container = modelContainer else { return }
        let context = ModelContext(container)

        for diary in diaries {
            let cachedDiary = CachedDiary(
                id: diary.id,
                rawText: diary.rawText,
                cleanedText: diary.cleanedText,
                emotion: diary.emotion,
                emotionScore: diary.emotionScore,
                emotionEnergy: diary.emotionEnergy,
                emotionIntensity: diary.emotionIntensity,
                emotionKeywords: diary.emotionKeywords,
                secondaryEmotions: diary.secondaryEmotions,
                emotionDimension: diary.emotionDimension,
                emotionConfidence: diary.emotionConfidence,
                topics: diary.topics,
                keyEvents: diary.keyEvents,
                recordingDuration: diary.recordingDuration,
                wordCount: diary.wordCount,
                weather: diary.weather,
                createdAt: diary.createdAt,
                updatedAt: diary.updatedAt
            )
            context.insert(cachedDiary)
        }

        try? context.save()
    }

    func saveDiary(_ diary: Diary) async {
        guard let container = modelContainer else { return }
        let context = ModelContext(container)

        let descriptor = FetchDescriptor<CachedDiary>(predicate: #Predicate { $0.id == diary.id })
        if let existing = try? context.fetch(descriptor).first {
            existing.rawText = diary.rawText
            existing.cleanedText = diary.cleanedText
            existing.emotion = diary.emotion
            existing.emotionScore = diary.emotionScore
            existing.emotionEnergy = diary.emotionEnergy
            existing.emotionIntensity = diary.emotionIntensity
            existing.emotionKeywords = diary.emotionKeywords
            existing.secondaryEmotions = diary.secondaryEmotions
            existing.emotionDimension = diary.emotionDimension
            existing.emotionConfidence = diary.emotionConfidence
            existing.topics = diary.topics
            existing.keyEvents = diary.keyEvents
            existing.recordingDuration = diary.recordingDuration
            existing.wordCount = diary.wordCount
            if let w = diary.weather {
                existing.weatherTemperature = w.temperature
                existing.weatherText = w.weather
                existing.weatherIcon = w.weatherIcon
                existing.weatherLocation = w.location
            } else {
                existing.weatherTemperature = nil
                existing.weatherText = nil
                existing.weatherIcon = nil
                existing.weatherLocation = nil
            }
            existing.createdAt = diary.createdAt
            existing.updatedAt = diary.updatedAt
            existing.cachedAt = Date()
        } else {
            let cachedDiary = CachedDiary(
                id: diary.id,
                rawText: diary.rawText,
                cleanedText: diary.cleanedText,
                emotion: diary.emotion,
                emotionScore: diary.emotionScore,
                emotionEnergy: diary.emotionEnergy,
                emotionIntensity: diary.emotionIntensity,
                emotionKeywords: diary.emotionKeywords,
                secondaryEmotions: diary.secondaryEmotions,
                emotionDimension: diary.emotionDimension,
                emotionConfidence: diary.emotionConfidence,
                topics: diary.topics,
                keyEvents: diary.keyEvents,
                recordingDuration: diary.recordingDuration,
                wordCount: diary.wordCount,
                weather: diary.weather,
                createdAt: diary.createdAt,
                updatedAt: diary.updatedAt
            )
            context.insert(cachedDiary)
        }
        try? context.save()
    }

    func deleteDiary(id: Int) async {
        guard let container = modelContainer else { return }
        let context = ModelContext(container)

        let descriptor = FetchDescriptor<CachedDiary>(predicate: #Predicate { $0.id == id })
        if let cachedDiary = try? context.fetch(descriptor).first {
            context.delete(cachedDiary)
            try? context.save()
        }
    }

    func getAllDiaries() async -> [Diary] {
        guard let container = modelContainer else { return [] }
        let context = ModelContext(container)

        let descriptor = FetchDescriptor<CachedDiary>(sortBy: [SortDescriptor(\.createdAt, order: .reverse)])
        guard let cachedDiaries = try? context.fetch(descriptor) else { return [] }

        return cachedDiaries.map { $0.toDiary() }
    }

    func getDiary(id: Int) async -> Diary? {
        guard let container = modelContainer else { return nil }
        let context = ModelContext(container)

        let descriptor = FetchDescriptor<CachedDiary>(predicate: #Predicate { $0.id == id })
        guard let cachedDiary = try? context.fetch(descriptor).first else { return nil }

        return cachedDiary.toDiary()
    }

    func saveStats(_ stats: Stats) async {
        guard let container = modelContainer else { return }
        let context = ModelContext(container)

        let descriptor = FetchDescriptor<CachedStats>()
        if let cachedStats = try? context.fetch(descriptor).first {
            cachedStats.totalDiaries = stats.totalDiaries
            cachedStats.totalWords = stats.totalWords
            cachedStats.streakDays = stats.streakDays
            cachedStats.averageEmotionScore = stats.averageEmotionScore
            cachedStats.averageEmotionEnergy = stats.averageEmotionEnergy
            cachedStats.averageEmotionIntensity = stats.averageEmotionIntensity
            cachedStats.updatedAt = Date()
        } else {
            let cachedStats = CachedStats(
                totalDiaries: stats.totalDiaries,
                totalWords: stats.totalWords,
                streakDays: stats.streakDays,
                averageEmotionScore: stats.averageEmotionScore,
                averageEmotionEnergy: stats.averageEmotionEnergy,
                averageEmotionIntensity: stats.averageEmotionIntensity
            )
            context.insert(cachedStats)
        }
        try? context.save()
    }

    func getStats() async -> Stats? {
        guard let container = modelContainer else { return nil }
        let context = ModelContext(container)

        let descriptor = FetchDescriptor<CachedStats>()
        guard let cachedStats = try? context.fetch(descriptor).first else { return nil }

        return Stats(
            totalDiaries: cachedStats.totalDiaries,
            totalWords: cachedStats.totalWords,
            streakDays: cachedStats.streakDays,
            averageEmotionScore: cachedStats.averageEmotionScore,
            averageEmotionEnergy: cachedStats.averageEmotionEnergy,
            averageEmotionIntensity: cachedStats.averageEmotionIntensity
        )
    }

    func clearAll() async {
        guard let container = modelContainer else { return }
        let context = ModelContext(container)

        try? context.delete(model: CachedDiary.self)
        try? context.delete(model: CachedStats.self)
        try? context.save()
    }
}