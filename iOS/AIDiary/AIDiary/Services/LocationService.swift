import Foundation
import CoreLocation

class LocationService: NSObject, CLLocationManagerDelegate {
    static let shared = LocationService()

    private let locationManager = CLLocationManager()
    var currentLocation: CLLocation?
    var currentCity: String?

    private var locationCompletion: ((CLLocation?) -> Void)?

    private override init() {
        super.init()
        locationManager.delegate = self
        locationManager.desiredAccuracy = kCLLocationAccuracyKilometer  // 城市级精度，节省电量
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

        if status == .authorizedWhenInUse || status == .authorizedAlways {
            // 授权成功后，如果有等待的 completion，请求位置
            if locationCompletion != nil {
                print("📍 授权成功，请求位置...")
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
        print("获取位置成功: \(location.coordinate.latitude), \(location.coordinate.longitude)")

        // 获取城市名称（反向地理编码）
        let geocoder = CLGeocoder()
        geocoder.reverseGeocodeLocation(location) { placemarks, error in
            if let placemark = placemarks?.first {
                let city = placemark.locality ?? placemark.administrativeArea ?? "未知"
                self.currentCity = city
                print("城市: \(city)")
            }
        }

        locationCompletion?(location)
        locationCompletion = nil
    }

    func locationManager(_ manager: CLLocationManager, didFailWithError error: Error) {
        print("获取位置失败: \(error.localizedDescription)")
        locationCompletion?(nil)
        locationCompletion = nil
    }
}