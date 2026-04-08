import Foundation

struct Diary: Codable, Identifiable, Hashable {
    let id: Int
    let rawText: String
    let cleanedText: String?
    let emotion: String?
    let emotionScore: Double?
    let emotionKeywords: [String]?
    let topics: [String]?
    let keyEvents: [String]?
    let recordingDuration: Int?
    let wordCount: Int
    let createdAt: Date
    let updatedAt: Date
    
    enum CodingKeys: String, CodingKey {
        case id
        case rawText = "raw_text"
        case cleanedText = "cleaned_text"
        case emotion
        case emotionScore = "emotion_score"
        case emotionKeywords = "emotion_keywords"
        case topics
        case keyEvents = "key_events"
        case recordingDuration = "recording_duration"
        case wordCount = "word_count"
        case createdAt = "created_at"
        case updatedAt = "updated_at"
    }
}

struct DiaryListResponse: Codable {
    let items: [Diary]
    let total: Int
    let page: Int
    let pageSize: Int
    
    enum CodingKeys: String, CodingKey {
        case items, total, page
        case pageSize = "page_size"
    }
}

struct Stats: Codable {
    let totalDiaries: Int
    let totalWords: Int
    let streakDays: Int
    let averageEmotionScore: Double?
    
    enum CodingKeys: String, CodingKey {
        case totalDiaries = "total_diaries"
        case totalWords = "total_words"
        case streakDays = "streak_days"
        case averageEmotionScore = "average_emotion_score"
    }
}

struct Insight: Codable, Identifiable {
    let type: String
    let insight: String
    
    var id: String { "\(type)-\(insight)" }
}

struct SearchResult: Codable, Identifiable {
    let id: Int
    let text: String
    let score: Double
    let createdAt: Date
    
    enum CodingKeys: String, CodingKey {
        case id, text, score
        case createdAt = "created_at"
    }
}

struct SearchResponse: Codable {
    let results: [SearchResult]
    let query: String
    let total: Int
}

struct EmotionTrendData: Codable {
    let date: String
    let averageScore: Double
    let diaryCount: Int
    
    enum CodingKeys: String, CodingKey {
        case date
        case averageScore = "average_score"
        case diaryCount = "diary_count"
    }
}

struct EmotionTrendResponse: Codable {
    let trend: [EmotionTrendData]
    let days: Int
}

struct AskResponse: Codable {
    let answer: String
    let relatedDiaries: [RelatedDiary]?
    
    enum CodingKeys: String, CodingKey {
        case answer
        case relatedDiaries = "related_diaries"
    }
}

struct RelatedDiary: Codable {
    let id: Int
    let text: String
    let score: Double
    
    enum CodingKeys: String, CodingKey {
        case id, text, score
    }
}