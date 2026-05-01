import Foundation
import SwiftData

@Model
class CachedDiary {
    @Attribute(.unique) var id: Int
    var rawText: String
    var cleanedText: String?
    var emotion: String?
    var emotionScore: Double?  // 兼容旧数据
    var emotionEnergy: Double?  // 新增
    var emotionIntensity: Double?  // 新增
    var emotionKeywords: [String]?
    var secondaryEmotions: [String]?
    var emotionDimension: String?  // 兼容旧数据
    var emotionConfidence: Double?
    var topics: [String]?
    var keyEvents: [String]?
    var recordingDuration: Int?
    var wordCount: Int
    var weatherTemperature: Int?
    var weatherText: String?
    var weatherIcon: String?
    var weatherLocation: String?
    var createdAt: Date
    var updatedAt: Date
    var cachedAt: Date

    init(id: Int, rawText: String, cleanedText: String?, emotion: String?, emotionScore: Double?, emotionEnergy: Double?, emotionIntensity: Double?, emotionKeywords: [String]?, secondaryEmotions: [String]?, emotionDimension: String?, emotionConfidence: Double?, topics: [String]?, keyEvents: [String]?, recordingDuration: Int?, wordCount: Int, weather: Weather?, createdAt: Date, updatedAt: Date) {
        self.id = id
        self.rawText = rawText
        self.cleanedText = cleanedText
        self.emotion = emotion
        self.emotionScore = emotionScore
        self.emotionEnergy = emotionEnergy
        self.emotionIntensity = emotionIntensity
        self.emotionKeywords = emotionKeywords
        self.secondaryEmotions = secondaryEmotions
        self.emotionDimension = emotionDimension
        self.emotionConfidence = emotionConfidence
        self.topics = topics
        self.keyEvents = keyEvents
        self.recordingDuration = recordingDuration
        self.wordCount = wordCount
        if let w = weather {
            self.weatherTemperature = w.temperature
            self.weatherText = w.weather
            self.weatherIcon = w.weatherIcon
            self.weatherLocation = w.location
        }
        self.createdAt = createdAt
        self.updatedAt = updatedAt
        self.cachedAt = Date()
    }

    func toDiary() -> Diary {
        let weather: Weather? = {
            if let temp = weatherTemperature, let text = weatherText, let icon = weatherIcon, let loc = weatherLocation {
                return Weather(temperature: temp, weather: text, weatherIcon: icon, location: loc)
            }
            return nil
        }()

        return Diary(
            id: id,
            rawText: rawText,
            cleanedText: cleanedText,
            emotion: emotion,
            emotionScore: emotionScore,
            emotionEnergy: emotionEnergy,
            emotionIntensity: emotionIntensity,
            emotionKeywords: emotionKeywords,
            secondaryEmotions: secondaryEmotions,
            emotionDimension: emotionDimension,
            emotionConfidence: emotionConfidence,
            topics: topics,
            keyEvents: keyEvents,
            recordingDuration: recordingDuration,
            wordCount: wordCount,
            weather: weather,
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
    var averageEmotionScore: Double?  // 兼容旧数据
    var averageEmotionEnergy: Double?  // 新增
    var averageEmotionIntensity: Double?  // 新增
    var updatedAt: Date

    init(totalDiaries: Int, totalWords: Int, streakDays: Int, averageEmotionScore: Double?, averageEmotionEnergy: Double?, averageEmotionIntensity: Double?) {
        self.totalDiaries = totalDiaries
        self.totalWords = totalWords
        self.streakDays = streakDays
        self.averageEmotionScore = averageEmotionScore
        self.averageEmotionEnergy = averageEmotionEnergy
        self.averageEmotionIntensity = averageEmotionIntensity
        self.updatedAt = Date()
    }
}