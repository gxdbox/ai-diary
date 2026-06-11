//
//  WorldModels.swift
//  AIDiary
//
//  虚拟世界数据模型
//

import Foundation

// MARK: - 人物别名
struct Alias: Codable, Identifiable, Hashable {
    let id: Int
    let alias: String
    let source: String
    let confidence: Double
    let createdAt: Date

    enum CodingKeys: String, CodingKey {
        case id, alias, source, confidence
        case createdAt = "created_at"
    }
}

// MARK: - 人物实体
struct Character: Codable, Identifiable, Hashable {
    let id: Int
    let name: String
    let appearanceCount: Int
    let avatarColor: String
    let firstAppearance: Date
    let lastAppearance: Date
    let aliases: [Alias]

    // UI 相关属性（非持久化）
    var x: CGFloat = 0
    var y: CGFloat = 0

    enum CodingKeys: String, CodingKey {
        case id, name, aliases
        case appearanceCount = "appearance_count"
        case avatarColor = "avatar_color"
        case firstAppearance = "first_appearance"
        case lastAppearance = "last_appearance"
    }

    init(id: Int, name: String, appearanceCount: Int, avatarColor: String,
         firstAppearance: Date, lastAppearance: Date, aliases: [Alias] = [],
         x: CGFloat = 0, y: CGFloat = 0) {
        self.id = id
        self.name = name
        self.appearanceCount = appearanceCount
        self.avatarColor = avatarColor
        self.firstAppearance = firstAppearance
        self.lastAppearance = lastAppearance
        self.aliases = aliases
        self.x = x
        self.y = y
    }

    init(from decoder: Decoder) throws {
        let container = try decoder.container(keyedBy: CodingKeys.self)
        id = try container.decode(Int.self, forKey: .id)
        name = try container.decode(String.self, forKey: .name)
        appearanceCount = try container.decode(Int.self, forKey: .appearanceCount)
        avatarColor = try container.decode(String.self, forKey: .avatarColor)
        firstAppearance = try container.decode(Date.self, forKey: .firstAppearance)
        lastAppearance = try container.decode(Date.self, forKey: .lastAppearance)
        aliases = try container.decodeIfPresent([Alias].self, forKey: .aliases) ?? []
    }
}

// MARK: - 人物关系
struct Relationship: Codable, Identifiable, Hashable {
    let id: Int
    let characterAId: Int
    let characterBId: Int
    let characterAName: String?
    let characterBName: String?
    let relationshipType: String
    let strength: Double
    let lastInteraction: Date?

    enum CodingKeys: String, CodingKey {
        case id
        case characterAId = "character_a_id"
        case characterBId = "character_b_id"
        case characterAName = "character_a_name"
        case characterBName = "character_b_name"
        case relationshipType = "relationship_type"
        case strength
        case lastInteraction = "last_interaction"
    }
}

// MARK: - 地点
struct Location: Codable, Identifiable, Hashable {
    let id: Int
    let name: String
    let visitCount: Int
    let lastVisit: Date?

    enum CodingKeys: String, CodingKey {
        case id, name
        case visitCount = "visit_count"
        case lastVisit = "last_visit"
    }
}

// MARK: - 世界统计信息
struct WorldStats: Codable {
    let totalCharacters: Int
    let totalRelationships: Int
    let totalLocations: Int
    let mostActiveCharacter: Character?
    let strongestRelationship: Relationship?

    enum CodingKeys: String, CodingKey {
        case totalCharacters = "total_characters"
        case totalRelationships = "total_relationships"
        case totalLocations = "total_locations"
        case mostActiveCharacter = "most_active_character"
        case strongestRelationship = "strongest_relationship"
    }
}

// MARK: - 人物时间轴响应
struct CharacterTimelineResponse: Codable {
    let character: Character
    let diaries: [Diary]
    let total: Int
}
