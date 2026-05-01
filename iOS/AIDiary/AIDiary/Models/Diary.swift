import Foundation

struct Diary: Codable, Identifiable, Hashable {
    let id: Int
    let rawText: String
    let cleanedText: String?
    let emotion: String?
    let emotionScore: Double?
    let emotionKeywords: [String]?
    let secondaryEmotions: [String]?
    let emotionDimension: String?
    let emotionConfidence: Double?
    let topics: [String]?
    let keyEvents: [String]?
    let recordingDuration: Int?
    let wordCount: Int
    let weather: Weather?
    let createdAt: Date
    let updatedAt: Date

    enum CodingKeys: String, CodingKey {
        case id
        case rawText = "raw_text"
        case cleanedText = "cleaned_text"
        case emotion
        case emotionScore = "emotion_score"
        case emotionKeywords = "emotion_keywords"
        case secondaryEmotions = "secondary_emotions"
        case emotionDimension = "emotion_dimension"
        case emotionConfidence = "emotion_confidence"
        case topics
        case keyEvents = "key_events"
        case recordingDuration = "recording_duration"
        case wordCount = "word_count"
        case weather
        case createdAt = "created_at"
        case updatedAt = "updated_at"
    }
}

struct Weather: Codable, Equatable, Hashable {
    let temperature: Int
    let weather: String
    let weatherIcon: String
    let location: String

    enum CodingKeys: String, CodingKey {
        case temperature
        case weather
        case weatherIcon = "weather_icon"
        case location
    }

    // 天气图标映射（和风天气图标代码 → emoji）
    var emoji: String {
        switch weatherIcon {
        case "100", "150": return "☀️"  // 晴
        case "101", "102", "103", "104", "151", "152", "153", "154": return "☁️"  // 多云
        case "300", "301", "302", "303", "304", "305", "306", "307", "308", "309", "310", "311", "312", "313", "314", "315", "316", "317", "318", "350", "351", "352", "353", "354", "355", "356", "357", "358", "359", "399": return "🌧️"  // 雨
        case "400", "401", "402", "403", "404", "405", "406", "407", "408", "409", "410", "450", "451", "452", "453", "454", "455", "456", "457", "458", "459", "499": return "❄️"  // 雪
        case "500", "501", "502", "503", "504", "507", "508", "509", "510", "511", "512", "513", "514", "515", "550", "551", "552", "553", "554", "555", "556", "557", "558", "559", "599": return "🌫️"  // 雾
        default: return "🌤️"
        }
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

// ============ 深度洞察模型 ============

struct DeepInsightCategory: Codable, Identifiable {
    let category: String
    let categoryName: String
    let categoryIcon: String
    let insights: [DeepInsight]
    let highlight: String?

    var id: String { category }

    enum CodingKeys: String, CodingKey {
        case category
        case categoryName = "category_name"
        case categoryIcon = "category_icon"
        case insights, highlight
    }
}

struct DeepInsight: Codable, Identifiable {
    let category: String
    let subType: String
    let title: String
    let insight: String
    let evidence: [String]
    let severity: String
    let suggestion: String?
    let confidence: Double
    let icon: String?
    let trend: String?

    var id: String { "\(subType)-\(title)" }

    enum CodingKeys: String, CodingKey {
        case category
        case subType = "sub_type"
        case title, insight, evidence, severity, suggestion, confidence, icon, trend
    }
}

struct DeepInsightResponse: Codable {
    let categories: [DeepInsightCategory]
    let overallSummary: String
    let generatedAt: String
    let analysisPeriodDays: Int

    enum CodingKeys: String, CodingKey {
        case categories
        case overallSummary = "overall_summary"
        case generatedAt = "generated_at"
        case analysisPeriodDays = "analysis_period_days"
    }
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
    let memoryIds: [Int]?

    enum CodingKeys: String, CodingKey {
        case answer
        case relatedDiaries = "related_diaries"
        case memoryIds = "memory_ids"
    }
}

struct RelatedDiary: Codable {
    let id: Int
    let text: String
    let date: String?
    let emotion: String?

    enum CodingKeys: String, CodingKey {
        case id, text, date, emotion
    }
}

struct FilterOptions: Codable {
    let emotions: [String]
    let topics: [String]
}

struct DictionaryEntry: Codable, Identifiable {
    let id: Int
    let word: String
    let pinyin: String
}

struct DictionaryListResponse: Codable {
    let entries: [DictionaryEntry]
    let total: Int
}