import Foundation
import CoreLocation

class LocationService: NSObject, CLLocationManagerDelegate {
    static let shared = LocationService()

    private let locationManager: CLLocationManager
    var currentLocation: CLLocation?
    var currentCity: String?

    // 暴露授权状态供外部查询
    var authorizationStatus: CLAuthorizationStatus {
        locationManager.authorizationStatus
    }

    private var locationCompletion: ((CLLocation?) -> Void)?
    private var authTimeoutTimer: Timer?

    private override init() {
        // 先创建 locationManager
        locationManager = CLLocationManager()
        super.init()
        // 再设置 delegate
        locationManager.delegate = self
        locationManager.desiredAccuracy = kCLLocationAccuracyKilometer

        // 打印初始化时的授权状态（注意：此时可能不准确，需要等回调）
        print("📍 LocationService 初始化 - 初始授权状态: \(locationManager.authorizationStatus.rawValue)")
        print("📍 系统位置服务启用: \(CLLocationManager.locationServicesEnabled())")
    }

    // 公开的授权请求方法
    func requestAuthorization() {
        print("📍 requestAuthorization 调用，当前状态: \(locationManager.authorizationStatus.rawValue)")
        locationManager.requestWhenInUseAuthorization()
    }

    func getCurrentLocation(completion: @escaping (CLLocation?) -> Void) {
        // 先保存 completion handler，确保授权回调后能使用
        locationCompletion = completion

        let status = locationManager.authorizationStatus
        print("📍 LocationService.getCurrentLocation - 授权状态: \(status.rawValue)")

        switch status {
        case .authorizedWhenInUse, .authorizedAlways:
            print("📍 已授权，请求位置...")
            locationManager.requestLocation()
        case .notDetermined:
            // 请求授权，授权完成后 locationManagerDidChangeAuthorization 会调用 requestLocation
            print("📍 未授权，请求权限弹窗...")

            // 设置超时：如果 30 秒内没有授权响应，就放弃
            authTimeoutTimer?.invalidate()
            authTimeoutTimer = Timer.scheduledTimer(withTimeInterval: 30.0, repeats: false) { [weak self] _ in
                print("📍 ⏱️ 权限请求超时，放弃天气获取")
                self?.locationCompletion?(nil)
                self?.locationCompletion = nil
                self?.authTimeoutTimer = nil
            }

            locationManager.requestWhenInUseAuthorization()
        case .denied, .restricted:
            print("📍 ❌ 位置权限被拒绝")
            completion(nil)
            locationCompletion = nil
        @unknown default:
            print("📍 ❌ 未知的授权状态")
            completion(nil)
            locationCompletion = nil
        }
    }

    // MARK: - CLLocationManagerDelegate

    func locationManagerDidChangeAuthorization(_ manager: CLLocationManager) {
        let status = manager.authorizationStatus
        print("📍 授权状态变更: \(status.rawValue)")

        // 清除超时计时器
        authTimeoutTimer?.invalidate()
        authTimeoutTimer = nil

        if status == .authorizedWhenInUse || status == .authorizedAlways {
            // 授权成功后，如果有等待的 completion，请求位置
            if locationCompletion != nil {
                print("📍 ✅ 授权成功，请求位置...")
                locationManager.requestLocation()
            }
        } else if status == .denied || status == .restricted {
            // 授权被拒绝
            print("📍 ❌ 授权被拒绝")
            locationCompletion?(nil)
            locationCompletion = nil
        }
    }

    func locationManager(_ manager: CLLocationManager, didUpdateLocations locations: [CLLocation]) {
        guard let location = locations.last else { return }
        currentLocation = location
        print("📍 ✅ 获取位置成功: \(location.coordinate.latitude), \(location.coordinate.longitude)")

        // 获取城市名称（反向地理编码）
        let geocoder = CLGeocoder()
        geocoder.reverseGeocodeLocation(location) { placemarks, error in
            if let placemark = placemarks?.first {
                let city = placemark.locality ?? placemark.administrativeArea ?? "未知"
                self.currentCity = city
                print("📍 城市: \(city)")
            }
        }

        locationCompletion?(location)
        locationCompletion = nil
    }

    func locationManager(_ manager: CLLocationManager, didFailWithError error: Error) {
        print("📍 ❌ 获取位置失败: \(error.localizedDescription)")
        locationCompletion?(nil)
        locationCompletion = nil
    }
}