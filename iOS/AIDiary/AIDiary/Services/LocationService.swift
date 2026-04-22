import Foundation
import CoreLocation

class LocationService: NSObject, CLLocationManagerDelegate {
    static let shared = LocationService()

    private let locationManager: CLLocationManager
    var currentLocation: CLLocation?
    var currentCity: String?

    var authorizationStatus: CLAuthorizationStatus {
        locationManager.authorizationStatus
    }

    private var locationCompletion: ((CLLocation?) -> Void)?
    private var authTimeoutTimer: Timer?

    private override init() {
        locationManager = CLLocationManager()
        super.init()
        locationManager.delegate = self
        locationManager.desiredAccuracy = kCLLocationAccuracyKilometer
    }

    func requestAuthorization() {
        locationManager.requestWhenInUseAuthorization()
    }

    func getCurrentLocation(completion: @escaping (CLLocation?) -> Void) {
        locationCompletion = completion

        let status = locationManager.authorizationStatus

        switch status {
        case .authorizedWhenInUse, .authorizedAlways:
            locationManager.requestLocation()
        case .notDetermined:
            authTimeoutTimer?.invalidate()
            authTimeoutTimer = Timer.scheduledTimer(withTimeInterval: 30.0, repeats: false) { [weak self] _ in
                self?.locationCompletion?(nil)
                self?.locationCompletion = nil
                self?.authTimeoutTimer = nil
            }
            locationManager.requestWhenInUseAuthorization()
        case .denied, .restricted:
            completion(nil)
            locationCompletion = nil
        @unknown default:
            completion(nil)
            locationCompletion = nil
        }
    }

    // MARK: - CLLocationManagerDelegate

    func locationManagerDidChangeAuthorization(_ manager: CLLocationManager) {
        authTimeoutTimer?.invalidate()
        authTimeoutTimer = nil

        let status = manager.authorizationStatus
        if status == .authorizedWhenInUse || status == .authorizedAlways {
            if locationCompletion != nil {
                locationManager.requestLocation()
            }
        } else if status == .denied || status == .restricted {
            locationCompletion?(nil)
            locationCompletion = nil
        }
    }

    func locationManager(_ manager: CLLocationManager, didUpdateLocations locations: [CLLocation]) {
        guard let location = locations.last else { return }
        currentLocation = location

        let geocoder = CLGeocoder()
        geocoder.reverseGeocodeLocation(location) { placemarks, _ in
            if let placemark = placemarks?.first {
                self.currentCity = placemark.locality ?? placemark.administrativeArea ?? "未知"
            }
        }

        locationCompletion?(location)
        locationCompletion = nil
    }

    func locationManager(_ manager: CLLocationManager, didFailWithError error: Error) {
        locationCompletion?(nil)
        locationCompletion = nil
    }
}