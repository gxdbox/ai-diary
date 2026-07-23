import Foundation

/// FastAPI HTTP 错误响应体
private struct ErrorResponse: Decodable {
    let detail: String
}

class APIService {
    static let shared = APIService()

    /// Token 过期通知名（用于全局监听并跳转登录页）
    static let tokenExpiredNotification = Notification.Name("APIServiceTokenExpired")

    private var baseURL: String {
        AppConfig.baseURL
    }

    private init() {}

    // MARK: - 认证辅助

    /// 为 URLRequest 注入 Authorization header
    private func addAuthHeader(to request: inout URLRequest) {
        if let token = KeychainService.shared.loadToken() {
            request.setValue("Bearer \(token)", forHTTPHeaderField: "Authorization")
        }
    }

    /// 带 auth header 的 GET 请求
    private func authGET(_ urlString: String) async throws -> (Data, URLResponse) {
        guard let url = URL(string: urlString) else { throw URLError(.badURL) }
        var request = URLRequest(url: url)
        addAuthHeader(to: &request)
        let (data, response) = try await URLSession.shared.data(for: request)
        checkTokenExpired(response)
        return (data, response)
    }

    /// 检查响应是否为 401，如果是则发送通知
    private func checkTokenExpired(_ response: URLResponse) {
        if let httpResponse = response as? HTTPURLResponse, httpResponse.statusCode == 401 {
            NotificationCenter.default.post(name: APIService.tokenExpiredNotification, object: nil)
        }
    }

    private let dateFormatter: DateFormatter = {
        let formatter = DateFormatter()
        formatter.dateFormat = "yyyy-MM-dd'T'HH:mm:ss.SSSSSS"
        formatter.locale = Locale(identifier: "en_US_POSIX")
        formatter.timeZone = TimeZone(secondsFromGMT: 0)
        return formatter
    }()

    private func decode<T: Codable>(_ data: Data) throws -> T {
        let decoder = JSONDecoder()
        decoder.dateDecodingStrategy = .formatted(dateFormatter)
        return try decoder.decode(T.self, from: data)
    }

    func fetchDiaries(page: Int = 1, pageSize: Int = 20, emotion: String? = nil, topic: String? = nil, startDate: String? = nil, endDate: String? = nil) async throws -> DiaryListResponse {
        var urlComponents = URLComponents(string: "\(baseURL)/api/diary/list")!
        urlComponents.queryItems = [
            URLQueryItem(name: "page", value: "\(page)"),
            URLQueryItem(name: "page_size", value: "\(pageSize)")
        ]

        if let emotion = emotion {
            urlComponents.queryItems?.append(URLQueryItem(name: "emotion", value: emotion))
        }
        if let topic = topic {
            urlComponents.queryItems?.append(URLQueryItem(name: "topic", value: topic))
        }
        if let startDate = startDate {
            urlComponents.queryItems?.append(URLQueryItem(name: "start_date", value: startDate))
        }
        if let endDate = endDate {
            urlComponents.queryItems?.append(URLQueryItem(name: "end_date", value: endDate))
        }

        guard let url = urlComponents.url else {
            throw URLError(.badURL)
        }

        print("Fetching diaries from: \(url.absoluteString)")

        let (data, _) = try await authGET(url.absoluteString)
        return try decode(data)
    }

    func fetchFilters() async throws -> FilterOptions {
        let url = URL(string: "\(baseURL)/api/diary/filters")!
        let (data, _) = try await authGET(url.absoluteString)
        return try decode(data)
    }

    func fetchStats() async throws -> Stats {
        let url = URL(string: "\(baseURL)/api/analysis/stats")!
        let (data, _) = try await authGET(url.absoluteString)
        return try decode(data)
    }

    func fetchInsights(days: Int = 7) async throws -> [Insight] {
        let url = URL(string: "\(baseURL)/api/analysis/insights?days=\(days)")!
        let (data, _) = try await authGET(url.absoluteString)
        let response: InsightsResponse = try decode(data)
        return response.insights
    }

    func fetchDeepInsights(days: Int = 90) async throws -> DeepInsightResponse {
        let url = URL(string: "\(baseURL)/api/analysis/deep-insights?days=\(days)")!
        let (data, _) = try await authGET(url.absoluteString)
        return try decode(data)
    }

    func createDiary(rawText: String, recordingDuration: Int? = nil) async throws -> Diary {
        var request = URLRequest(url: URL(string: "\(baseURL)/api/diary/create")!)
        request.httpMethod = "POST"
        request.setValue("application/json", forHTTPHeaderField: "Content-Type")
        addAuthHeader(to: &request)

        var body: [String: Any] = ["raw_text": rawText]
        if let duration = recordingDuration {
            body["recording_duration"] = duration
        }
        request.httpBody = try JSONSerialization.data(withJSONObject: body)

        let (data, response) = try await URLSession.shared.data(for: request)
        checkTokenExpired(response)
        return try decode(data)
    }

    func deleteDiary(id: Int) async throws {
        var request = URLRequest(url: URL(string: "\(baseURL)/api/diary/\(id)")!)
        request.httpMethod = "DELETE"
        addAuthHeader(to: &request)
        let (_, response) = try await URLSession.shared.data(for: request)
        checkTokenExpired(response)
        guard let httpResponse = response as? HTTPURLResponse, httpResponse.statusCode == 200 else {
            checkTokenExpired(response)
            throw URLError(.badServerResponse)
        }
    }

    func updateDiary(id: Int, cleanedText: String) async throws -> Diary {
        let urlString = "\(baseURL)/api/diary/\(id)?cleaned_text=\(cleanedText.addingPercentEncoding(withAllowedCharacters: .urlQueryAllowed) ?? "")"
        var request = URLRequest(url: URL(string: urlString)!)
        request.httpMethod = "PUT"
        request.setValue("application/json", forHTTPHeaderField: "Content-Type")
        addAuthHeader(to: &request)

        let (data, response) = try await URLSession.shared.data(for: request)
        checkTokenExpired(response)
        return try decode(data)
    }

    // MARK: - 音频

    func uploadAudio(diaryId: Int, audioFileURL: URL) async throws -> Diary {
        let url = URL(string: "\(baseURL)/api/diary/\(diaryId)/audio")!
        let boundary = UUID().uuidString

        var request = URLRequest(url: url)
        request.httpMethod = "POST"
        request.setValue("multipart/form-data; boundary=\(boundary)", forHTTPHeaderField: "Content-Type")
        addAuthHeader(to: &request)

        var body = Data()
        let audioData = try Data(contentsOf: audioFileURL)
        let fileName = audioFileURL.lastPathComponent

        body.append("--\(boundary)\r\n".data(using: .utf8)!)
        body.append("Content-Disposition: form-data; name=\"audio_file\"; filename=\"\(fileName)\"\r\n".data(using: .utf8)!)
        body.append("Content-Type: audio/mp4\r\n\r\n".data(using: .utf8)!)
        body.append(audioData)
        body.append("\r\n--\(boundary)--\r\n".data(using: .utf8)!)

        request.httpBody = body

        let (data, response) = try await URLSession.shared.data(for: request)
        checkTokenExpired(response)
        return try decode(data)
    }

    func getAudioURL(diaryId: Int) async throws -> URL {
        let url = URL(string: "\(baseURL)/api/diary/\(diaryId)/audio-url")!
        let (data, _) = try await authGET(url.absoluteString)

        struct AudioURLResponse: Codable {
            let audioURL: String
            enum CodingKeys: String, CodingKey {
                case audioURL = "audio_url"
            }
        }

        let response = try JSONDecoder().decode(AudioURLResponse.self, from: data)
        guard let signedURL = URL(string: response.audioURL) else {
            throw URLError(.badURL)
        }
        return signedURL
    }

    func semanticSearch(query: String) async throws -> SearchResponse {
        var request = URLRequest(url: URL(string: "\(baseURL)/api/search/semantic")!)
        request.httpMethod = "POST"
        request.setValue("application/json", forHTTPHeaderField: "Content-Type")
        addAuthHeader(to: &request)
        request.httpBody = try JSONSerialization.data(withJSONObject: ["query": query, "limit": 10])

        let (data, response) = try await URLSession.shared.data(for: request)
        checkTokenExpired(response)
        return try decode(data)
    }

    func fetchEmotionTrend(days: Int = 7) async throws -> [EmotionTrendData] {
        let url = URL(string: "\(baseURL)/api/analysis/emotion/trend?days=\(days)")!
        let (data, _) = try await authGET(url.absoluteString)
        let response: EmotionTrendResponse = try decode(data)
        return response.trend
    }

    func askQuestion(question: String, conversationHistory: [[String: String]]? = nil) async throws -> AskResponse {
        let urlString = "\(baseURL)/api/assistant/ask?question=\(question.addingPercentEncoding(withAllowedCharacters: .urlQueryAllowed) ?? "")"
        guard let url = URL(string: urlString) else {
            throw URLError(.badURL)
        }

        var request = URLRequest(url: url)
        request.httpMethod = "POST"
        request.setValue("application/json", forHTTPHeaderField: "Content-Type")
        addAuthHeader(to: &request)

        // 支持传递对话历史
        var body: [String: Any] = [:]
        if let history = conversationHistory, !history.isEmpty {
            body["conversation_history"] = history
        }
        request.httpBody = try JSONSerialization.data(withJSONObject: body)

        let (data, response) = try await URLSession.shared.data(for: request)
        checkTokenExpired(response)
        return try decode(data)
    }

    // MARK: - Agent 对话（借鉴 Hermes 的 tool-calling loop）
    // Agent 会在需要时主动调用工具：搜日记、跑洞察、查/存记忆
    func agentChat(message: String, conversationHistory: [[String: String]]? = nil, reflect: Bool = true) async throws -> AgentChatResponse {
        let url = URL(string: "\(baseURL)/api/agent/chat")!
        var request = URLRequest(url: url)
        request.httpMethod = "POST"
        request.setValue("application/json", forHTTPHeaderField: "Content-Type")
        addAuthHeader(to: &request)

        var body: [String: Any] = ["message": message, "reflect": reflect]
        if let history = conversationHistory, !history.isEmpty {
            body["conversation_history"] = history
        }
        request.httpBody = try JSONSerialization.data(withJSONObject: body)

        let (data, response) = try await URLSession.shared.data(for: request)
        checkTokenExpired(response)
        guard let httpResponse = response as? HTTPURLResponse, httpResponse.statusCode == 200 else {
            let errorResponse = try? JSONDecoder().decode(ErrorResponse.self, from: data)
            throw NSError(domain: "", code: (response as? HTTPURLResponse)?.statusCode ?? 0,
                userInfo: [NSLocalizedDescriptionKey: errorResponse?.detail ?? "Agent 对话失败"])
        }
        return try decode(data)
    }

    func sendFeedback(memoryIds: [Int], wasHelpful: Bool) async throws {
        let urlString = "\(baseURL)/api/assistant/feedback"
        guard let url = URL(string: urlString) else {
            throw URLError(.badURL)
        }

        var request = URLRequest(url: url)
        request.httpMethod = "POST"
        request.setValue("application/json", forHTTPHeaderField: "Content-Type")
        addAuthHeader(to: &request)

        let body: [String: Any] = [
            "memory_ids": memoryIds,
            "was_helpful": wasHelpful
        ]
        request.httpBody = try JSONSerialization.data(withJSONObject: body)

        let (_, response) = try await URLSession.shared.data(for: request)
        checkTokenExpired(response)
        guard let httpResponse = response as? HTTPURLResponse, httpResponse.statusCode == 200 else {
            throw URLError(.badServerResponse)
        }
    }

    // ============ 词典相关 API ============

    func fetchDictionary() async throws -> DictionaryListResponse {
        let url = URL(string: "\(baseURL)/api/dictionary/list")!
        let (data, _) = try await authGET(url.absoluteString)
        return try decode(data)
    }

    func addDictionaryEntry(word: String) async throws -> DictionaryEntry {
        var request = URLRequest(url: URL(string: "\(baseURL)/api/dictionary/add")!)
        request.httpMethod = "POST"
        request.setValue("application/json", forHTTPHeaderField: "Content-Type")
        addAuthHeader(to: &request)
        request.httpBody = try JSONSerialization.data(withJSONObject: ["word": word])

        let (data, response) = try await URLSession.shared.data(for: request)
        checkTokenExpired(response)
        guard let httpResponse = response as? HTTPURLResponse else {
            throw URLError(.badServerResponse)
        }
        if httpResponse.statusCode != 200 {
            let detail = try? JSONDecoder().decode(ErrorResponse.self, from: data)
            throw NSError(domain: "", code: httpResponse.statusCode,
                userInfo: [NSLocalizedDescriptionKey: detail?.detail ?? "添加失败"])
        }
        return try decode(data)
    }

    func deleteDictionaryEntry(id: Int) async throws {
        var request = URLRequest(url: URL(string: "\(baseURL)/api/dictionary/\(id)")!)
        request.httpMethod = "DELETE"
        addAuthHeader(to: &request)
        let (_, response) = try await URLSession.shared.data(for: request)
        checkTokenExpired(response)
        guard let httpResponse = response as? HTTPURLResponse, httpResponse.statusCode == 200 else {
            throw URLError(.badServerResponse)
        }
    }

    func updateDictionaryEntry(id: Int, word: String) async throws -> DictionaryEntry {
        var request = URLRequest(url: URL(string: "\(baseURL)/api/dictionary/\(id)")!)
        request.httpMethod = "PUT"
        request.setValue("application/json", forHTTPHeaderField: "Content-Type")
        addAuthHeader(to: &request)
        request.httpBody = try JSONSerialization.data(withJSONObject: ["word": word])

        let (data, response) = try await URLSession.shared.data(for: request)
        checkTokenExpired(response)
        return try decode(data)
    }

    // ============ 天气相关 API ============

    func updateWeather(diaryId: Int, weather: Weather) async throws {
        var request = URLRequest(url: URL(string: "\(baseURL)/api/diary/weather")!)
        request.httpMethod = "POST"
        request.setValue("application/json", forHTTPHeaderField: "Content-Type")
        addAuthHeader(to: &request)

        let body: [String: Any] = [
            "diary_id": diaryId,
            "weather": [
                "temperature": weather.temperature,
                "weather": weather.weather,
                "weather_icon": weather.weatherIcon,
                "location": weather.location
            ]
        ]
        request.httpBody = try JSONSerialization.data(withJSONObject: body)

        let (_, response) = try await URLSession.shared.data(for: request)
        checkTokenExpired(response)
        guard let httpResponse = response as? HTTPURLResponse, httpResponse.statusCode == 200 else {
            throw URLError(.badServerResponse)
        }
    }

    // ============ 图片相关 API ============

    func uploadImage(diaryId: Int, imageData: Data, fileName: String) async throws -> ImageUploadResponse {
        let boundary = "Boundary-\(UUID().uuidString)"
        var request = URLRequest(url: URL(string: "\(baseURL)/api/diary/images/upload")!)
        request.httpMethod = "POST"
        request.setValue("multipart/form-data; boundary=\(boundary)", forHTTPHeaderField: "Content-Type")
        addAuthHeader(to: &request)

        var body = Data()
        // diary_id 字段
        body.append("--\(boundary)\r\n".data(using: .utf8)!)
        body.append("Content-Disposition: form-data; name=\"diary_id\"\r\n\r\n".data(using: .utf8)!)
        body.append("\(diaryId)\r\n".data(using: .utf8)!)
        // file 字段
        let mimeType = fileName.lowercased().hasSuffix(".png") ? "image/png" : "image/jpeg"
        body.append("--\(boundary)\r\n".data(using: .utf8)!)
        body.append("Content-Disposition: form-data; name=\"file\"; filename=\"\(fileName)\"\r\n".data(using: .utf8)!)
        body.append("Content-Type: \(mimeType)\r\n\r\n".data(using: .utf8)!)
        body.append(imageData)
        body.append("\r\n".data(using: .utf8)!)
        body.append("--\(boundary)--\r\n".data(using: .utf8)!)

        request.httpBody = body

        let (data, response) = try await URLSession.shared.data(for: request)
        checkTokenExpired(response)
        guard let httpResponse = response as? HTTPURLResponse, httpResponse.statusCode == 200 else {
            throw URLError(.badServerResponse)
        }
        return try decode(data)
    }

    func deleteImage(diaryId: Int, imageKey: String) async throws {
        var request = URLRequest(url: URL(string: "\(baseURL)/api/diary/images")!)
        request.httpMethod = "DELETE"
        request.setValue("application/json", forHTTPHeaderField: "Content-Type")
        addAuthHeader(to: &request)

        let body: [String: Any] = [
            "diary_id": diaryId,
            "image_key": imageKey
        ]
        request.httpBody = try JSONSerialization.data(withJSONObject: body)

        let (_, response) = try await URLSession.shared.data(for: request)
        checkTokenExpired(response)
        guard let httpResponse = response as? HTTPURLResponse, httpResponse.statusCode == 200 else {
            throw URLError(.badServerResponse)
        }
    }

    // MARK: - World API

    func fetchCharacters(limit: Int = 100, sortBy: String = "appearance_count") async throws -> [Character] {
        var urlComponents = URLComponents(string: "\(baseURL)/api/world/characters")!
        urlComponents.queryItems = [
            URLQueryItem(name: "limit", value: "\(limit)"),
            URLQueryItem(name: "sort_by", value: sortBy)
        ]

        guard let url = urlComponents.url else {
            throw URLError(.badURL)
        }

        let (data, _) = try await authGET(url.absoluteString)
        return try decode(data)
    }

    func fetchRelationships(minStrength: Double = 0.0, limit: Int = 200) async throws -> [Relationship] {
        var urlComponents = URLComponents(string: "\(baseURL)/api/world/relationships")!
        urlComponents.queryItems = [
            URLQueryItem(name: "min_strength", value: "\(minStrength)"),
            URLQueryItem(name: "limit", value: "\(limit)")
        ]

        guard let url = urlComponents.url else {
            throw URLError(.badURL)
        }

        let (data, _) = try await authGET(url.absoluteString)
        return try decode(data)
    }

    func fetchLocations(limit: Int = 100) async throws -> [Location] {
        let url = URL(string: "\(baseURL)/api/world/locations?limit=\(limit)")!
        let (data, _) = try await authGET(url.absoluteString)
        return try decode(data)
    }

    func fetchWorldStats() async throws -> WorldStats {
        let url = URL(string: "\(baseURL)/api/world/stats")!
        let (data, _) = try await authGET(url.absoluteString)
        return try decode(data)
    }

    func fetchCharacterTimeline(characterName: String, limit: Int = 50) async throws -> CharacterTimelineResponse {
        let encodedName = characterName.addingPercentEncoding(withAllowedCharacters: .urlPathAllowed) ?? characterName
        let url = URL(string: "\(baseURL)/api/world/timeline/\(encodedName)?limit=\(limit)")!
        let (data, _) = try await authGET(url.absoluteString)
        return try decode(data)
    }

    func searchCharacters(query: String, limit: Int = 20) async throws -> [Character] {
        var urlComponents = URLComponents(string: "\(baseURL)/api/world/search/character")!
        urlComponents.queryItems = [
            URLQueryItem(name: "query", value: query),
            URLQueryItem(name: "limit", value: "\(limit)")
        ]

        guard let url = urlComponents.url else {
            throw URLError(.badURL)
        }

        let (data, _) = try await authGET(url.absoluteString)
        return try decode(data)
    }
}

private struct InsightsResponse: Codable {
    let insights: [Insight]
}