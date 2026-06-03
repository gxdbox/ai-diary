import Foundation
import CoreLocation

class WeatherService: Sendable {
    static let shared = WeatherService()

    private let qweatherApiKey = "a7272b45e9db411ebfdf478d694644c9"
    private let qweatherBaseURL = "https://devapi.qweather.com/v7/weather/now"

    private init() {}

    nonisolated func getWeather(location: CLLocation, completion: @escaping (Weather?) -> Void) {
        let locationParam = "\(location.coordinate.longitude),\(location.coordinate.latitude)"
        let urlString = "\(qweatherBaseURL)?location=\(locationParam)&key=\(qweatherApiKey)"

        guard let url = URL(string: urlString) else {
            completion(nil)
            return
        }

        URLSession.shared.dataTask(with: url) { data, _, error in
            guard let data = data, error == nil else {
                completion(nil)
                return
            }

            do {
                let result = try JSONDecoder().decode(QWeatherResponse.self, from: data)
                if result.code != "200" {
                    completion(nil)
                    return
                }

                guard let now = result.now else {
                    completion(nil)
                    return
                }

                let weather = Weather(
                    temperature: Int(now.temp) ?? 0,
                    weather: now.text,
                    weatherIcon: now.icon,
                    location: ""
                )
                completion(weather)
            } catch {
                completion(nil)
            }
        }.resume()
    }
}

nonisolated struct QWeatherResponse: Codable {
    let code: String
    let now: QWeatherNow?

    nonisolated struct QWeatherNow: Codable {
        let temp: String
        let text: String
        let icon: String
    }
}