import Foundation
import CoreLocation

class WeatherService {
    static let shared = WeatherService()

    // 和风天气 API 配置
    // 凭据ID：KM58GPU4UT
    private let qweatherApiKey = "a7272b45e9db411ebfdf478d694644c9"
    private let qweatherBaseURL = "https://devapi.qweather.com/v7/weather/now"

    private init() {}

    func getWeather(location: CLLocation, completion: @escaping (Weather?) -> Void) {
        // 和风天气 location 参数格式：经度,纬度
        let locationParam = "\(location.coordinate.longitude),\(location.coordinate.latitude)"
        let urlString = "\(qweatherBaseURL)?location=\(locationParam)&key=\(qweatherApiKey)"

        guard let url = URL(string: urlString) else {
            print("天气URL构建失败")
            completion(nil)
            return
        }

        print("请求天气: \(urlString)")

        URLSession.shared.dataTask(with: url) { data, response, error in
            guard let data = data, error == nil else {
                print("天气请求失败: \(error?.localizedDescription ?? "未知错误")")
                completion(nil)
                return
            }

            // 打印响应便于调试
            if let jsonString = String(data: data, encoding: .utf8) {
                print("天气响应: \(jsonString)")
            }

            do {
                let result = try JSONDecoder().decode(QWeatherResponse.self, from: data)

                // 检查响应状态码
                if result.code != "200" {
                    print("和风天气返回错误码: \(result.code)")
                    completion(nil)
                    return
                }

                guard let now = result.now else {
                    print("天气数据为空")
                    completion(nil)
                    return
                }

                let weather = Weather(
                    temperature: Int(now.temp) ?? 0,
                    weather: now.text,
                    weatherIcon: now.icon,
                    location: ""  // 城市名需要额外API，这里暂时留空
                )

                print("天气获取成功: \(weather.temperature)°C \(weather.weather)")
                completion(weather)
            } catch {
                print("天气解析失败: \(error.localizedDescription)")
                completion(nil)
            }
        }.resume()
    }
}

// 和风天气响应结构
// https://dev.qweather.com/docs/api/weather/weather-now/
struct QWeatherResponse: Codable, Sendable {
    let code: String           // 状态码，200表示成功
    let now: QWeatherNow?      // 当前天气数据

    struct QWeatherNow: Codable, Sendable {
        let temp: String       // 温度
        let text: String       // 天气现象文字描述
        let icon: String       // 天气图标代码
    }
}