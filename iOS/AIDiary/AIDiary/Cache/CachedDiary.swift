import Foundation
import SwiftData

@Model
class CachedDiary {
    @Attribute(.unique) var id: Int
    var rawText: String
    var cleanedText: String?
    var emotion: String?
    var emotionScore: Double?
    var emotionKeywords: [String]?
    var topics: [String]?
    var keyEvents: [String]?
    var recordingDuration: Int?
    var wordCount: Int
    var createdAt: Date
    var updatedAt: Date
    var cachedAt: Date
    
    init(id: Int, rawText: String, cleanedText: String?, emotion: String?, emotionScore: Double?, emotionKeywords: [String]?, topics: [String]?, keyEvents: [String]?, recordingDuration: Int?, wordCount: Int, createdAt: Date, updatedAt: Date) {
        self.id = id
        self.rawText = rawText
        self.cleanedText = cleanedText
        self.emotion = emotion
        self.emotionScore = emotionScore
        self.emotionKeywords = emotionKeywords
        self.topics = topics
        self.keyEvents = keyEvents
        self.recordingDuration = recordingDuration
        self.wordCount = wordCount
        self.createdAt = createdAt
        self.updatedAt = updatedAt
        self.cachedAt = Date()
    }
    
    func toDiary() -> Diary {
        Diary(
            id: id,
            rawText: rawText,
            cleanedText: cleanedText,
            emotion: emotion,
            emotionScore: emotionScore,
            emotionKeywords: emotionKeywords,
            topics: topics,
            keyEvents: keyEvents,
            recordingDuration: recordingDuration,
            wordCount: wordCount,
            createdAt: createdAt,
            updatedAt: updatedAt
        )
    }
}

@Model
class CachedStats {
    var totalDiaries: Int
    var totalWords: Int
    var streakDays: Int
    var averageEmotionScore: Double?
    var updatedAt: Date
    
    init(totalDiaries: Int, totalWords: Int, streakDays: Int, averageEmotionScore: Double?) {
        self.totalDiaries = totalDiaries
        self.totalWords = totalWords
        self.streakDays = streakDays
        self.averageEmotionScore = averageEmotionScore
        self.updatedAt = Date()
    }
}
