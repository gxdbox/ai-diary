import Foundation
import SwiftData

@Model
class CachedConversation {
    @Attribute(.unique) var id: UUID
    var title: String
    var createdAt: Date
    var updatedAt: Date
    @Relationship(deleteRule: .cascade) var messages: [CachedMessage] = []

    init(id: UUID = UUID(), title: String, createdAt: Date = Date(), updatedAt: Date = Date()) {
        self.id = id
        self.title = title
        self.createdAt = createdAt
        self.updatedAt = updatedAt
    }
}

@Model
class CachedMessage {
    @Attribute(.unique) var id: UUID
    var role: String
    var content: String
    var memoryIds: [Int]
    var feedbackGiven: Bool?
    var createdAt: Date
    var conversation: CachedConversation?

    init(
        id: UUID = UUID(),
        role: String,
        content: String,
        memoryIds: [Int] = [],
        feedbackGiven: Bool? = nil,
        createdAt: Date = Date()
    ) {
        self.id = id
        self.role = role
        self.content = content
        self.memoryIds = memoryIds
        self.feedbackGiven = feedbackGiven
        self.createdAt = createdAt
    }
}
