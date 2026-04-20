import Foundation
import CoreLocation

class WeatherService {
    static let shared = WeatherService()

    // OpenWeatherMap API（免费，1000次/天）
    // 用户需要替换为自己的 API Key：https://openweathermap.org/api
    private let apiKey = "YOUR_OPENWEATHERMAP_API_KEY"  // 替换为实际 Key
    private let baseURL = "https://api.openweathermap.org/data/2.5/weather"

    private init() {}

    func getWeather(location: CLLocation, completion: @escaping (Weather?) -> Void) {
        let urlString = "\(baseURL)?lat=\(location.coordinate.latitude)&lon=\(location.coordinate.longitude)&appid=\(apiKey)&units=metric&lang=zh_cn"

        guard let url = URL(string: urlString) else {
            completion(nil)
            return
        }

        URLSession.shared.dataTask(with: url) { data, response, error in
            guard let data = data, error == nil else {
                print("天气请求失败: \(error?.localizedDescription ?? "未知错误")")
                completion(nil)
                return
            }

            do {
                let result = try JSONDecoder().decode(OpenWeatherResponse.self, from: data)

                let weather = Weather(
                    temperature: Int(result.main.temp),
                    weather: result.weather.first?.description ?? "未知",
                    weatherIcon: result.weather.first?.icon ?? "",
                    location: result.name
                )

                completion(weather)
            } catch {
                print("天气解析失败: \(error.localizedDescription)")
                completion(nil)
            }
        }.resume()
    }

    // 使用和风天气 API（中国用户推荐）
    // https://dev.qweather.com/
    func getWeatherFromQWeather(location: CLLocation, completion: @escaping (Weather?) -> Void) {
        // 和风天气需要 API Key，用户可自行申请
        // 这里提供一个占位实现，实际使用时替换
        let apiKey = "YOUR_QWEATHER_API_KEY"
        let urlString = "https://devapi.qweather.com/v7/weather/now?location=\(location.coordinate.longitude),\(location.coordinate.latitude)&key=\(apiKey)"

        guard let url = URL(string: urlString) else {
            completion(nil)
            return
        }

        URLSession.shared.dataTask(with: url) { data, response, error in
            guard let data = data, error == nil else {
                completion(nil)
                return
            }

            do {
                let result = try JSONDecoder().decode(QWeatherResponse.self, from: data)

                guard let now = result.now else {
                    completion(nil)
                    return
                }

                let weather = Weather(
                    temperature: Int(now.temp),
                    weather: now.text,
                    weatherIcon: now.icon,
                    location: ""  // 需要额外调用城市查询 API
                )

                completion(weather)
            } catch {
                print("和风天气解析失败: \(error.localizedDescription)")
                completion(nil)
            }
        }.resume()
    }
}

// OpenWeatherMap 响应结构
struct OpenWeatherResponse: Codable {
    let main: Main
    let weather: [WeatherDetail]
    let name: String

    struct Main: Codable {
        let temp: Double
    }

    struct WeatherDetail: Codable {
        let description: String
        let icon: String
    }
}

// 和风天气响应结构
struct QWeatherResponse: Codable {
    let code: String
    let now: QWeatherNow?

    struct QWeatherNow: Codable {
        let temp: String
        let text: String
        let icon: String
    }
}