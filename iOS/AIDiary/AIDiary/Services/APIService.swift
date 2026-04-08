import Foundation

class APIService {
    static let shared = APIService()
    
    private let baseURL = "http://192.168.0.2:8000"
    
    private init() {}
    
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
    
    func fetchDiaries(page: Int = 1, pageSize: Int = 20) async throws -> DiaryListResponse {
        let url = URL(string: "\(baseURL)/api/diary/list?page=\(page)&page_size=\(pageSize)")!
        let (data, _) = try await URLSession.shared.data(from: url)
        return try decode(data)
    }
    
    func fetchStats() async throws -> Stats {
        let url = URL(string: "\(baseURL)/api/analysis/stats")!
        let (data, _) = try await URLSession.shared.data(from: url)
        return try decode(data)
    }
    
    func fetchInsights(days: Int = 7) async throws -> [Insight] {
        let url = URL(string: "\(baseURL)/api/analysis/insights?days=\(days)")!
        let (data, _) = try await URLSession.shared.data(from: url)
        let response: InsightsResponse = try decode(data)
        return response.insights
    }
    
    func createDiary(rawText: String, recordingDuration: Int? = nil) async throws -> Diary {
        var request = URLRequest(url: URL(string: "\(baseURL)/api/diary/create")!)
        request.httpMethod = "POST"
        request.setValue("application/json", forHTTPHeaderField: "Content-Type")
        
        var body: [String: Any] = ["raw_text": rawText]
        if let duration = recordingDuration {
            body["recording_duration"] = duration
        }
        request.httpBody = try JSONSerialization.data(withJSONObject: body)
        
        let (data, _) = try await URLSession.shared.data(for: request)
        return try decode(data)
    }
    
    func deleteDiary(id: Int) async throws {
        var request = URLRequest(url: URL(string: "\(baseURL)/api/diary/\(id)")!)
        request.httpMethod = "DELETE"
        let (_, response) = try await URLSession.shared.data(for: request)
        guard let httpResponse = response as? HTTPURLResponse, httpResponse.statusCode == 200 else {
            throw URLError(.badServerResponse)
        }
    }

    func updateDiary(id: Int, cleanedText: String) async throws -> Diary {
        let urlString = "\(baseURL)/api/diary/\(id)?cleaned_text=\(cleanedText.addingPercentEncoding(withAllowedCharacters: .urlQueryAllowed) ?? "")"
        var request = URLRequest(url: URL(string: urlString)!)
        request.httpMethod = "PUT"
        request.setValue("application/json", forHTTPHeaderField: "Content-Type")

        let (data, _) = try await URLSession.shared.data(for: request)
        return try decode(data)
    }
    
    func semanticSearch(query: String) async throws -> SearchResponse {
        var request = URLRequest(url: URL(string: "\(baseURL)/api/search/semantic")!)
        request.httpMethod = "POST"
        request.setValue("application/json", forHTTPHeaderField: "Content-Type")
        request.httpBody = try JSONSerialization.data(withJSONObject: ["query": query, "limit": 10])
        
        let (data, _) = try await URLSession.shared.data(for: request)
        return try decode(data)
    }
    
    func fetchEmotionTrend(days: Int = 7) async throws -> [EmotionTrendData] {
        let url = URL(string: "\(baseURL)/api/analysis/emotion/trend?days=\(days)")!
        let (data, _) = try await URLSession.shared.data(from: url)
        let response: EmotionTrendResponse = try decode(data)
        return response.trend
    }
    
    func askQuestion(question: String) async throws -> AskResponse {
        let urlString = "\(baseURL)/api/search/ask?question=\(question.addingPercentEncoding(withAllowedCharacters: .urlQueryAllowed) ?? "")"
        guard let url = URL(string: urlString) else {
            throw URLError(.badURL)
        }
        
        var request = URLRequest(url: url)
        request.httpMethod = "POST"
        request.setValue("application/json", forHTTPHeaderField: "Content-Type")
        request.httpBody = try JSONSerialization.data(withJSONObject: [:])
        
        let (data, _) = try await URLSession.shared.data(for: request)
        return try decode(data)
    }
}

private struct InsightsResponse: Codable {
    let insights: [Insight]
}