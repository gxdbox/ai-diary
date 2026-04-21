import Foundation
import CoreLocation
import Combine

class LocationService: NSObject, ObservableObject, CLLocationManagerDelegate {
    static let shared = LocationService()

    private let locationManager = CLLocationManager()
    @Published var currentLocation: CLLocation?
    @Published var currentCity: String?
    @Published var authorizationStatus: CLAuthorizationStatus = .notDetermined

    private var locationCompletion: ((CLLocation?) -> Void)?

    private override init() {
        super.init()
        locationManager.delegate = self
        locationManager.desiredAccuracy = kCLLocationAccuracyKilometer  // 城市级精度，节省电量
    }

    func requestAuthorization() {
        locationManager.requestWhenInUseAuthorization()
    }

    func getCurrentLocation(completion: @escaping (CLLocation?) -> Void) {
        locationCompletion = completion

        switch locationManager.authorizationStatus {
        case .authorizedWhenInUse, .authorizedAlways:
            locationManager.requestLocation()
        case .notDetermined:
            requestAuthorization()
        case .denied, .restricted:
            completion(nil)
        @unknown default:
            completion(nil)
        }
    }

    // MARK: - CLLocationManagerDelegate

    func locationManagerDidChangeAuthorization(_ manager: CLLocationManager) {
        authorizationStatus = manager.authorizationStatus

        if manager.authorizationStatus == .authorizedWhenInUse || manager.authorizationStatus == .authorizedAlways {
            locationManager.requestLocation()
        }
    }

    func locationManager(_ manager: CLLocationManager, didUpdateLocations locations: [CLLocation]) {
        guard let location = locations.last else { return }
        currentLocation = location

        // 获取城市名称（反向地理编码）
        let geocoder = CLGeocoder()
        geocoder.reverseGeocodeLocation(location) { placemarks, error in
            if let placemark = placemarks?.first {
                let city = placemark.locality ?? placemark.administrativeArea ?? "未知"
                DispatchQueue.main.async {
                    self.currentCity = city
                }
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