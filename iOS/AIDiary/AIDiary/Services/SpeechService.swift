import Foundation
import Speech
import AVFoundation
import Combine

class SpeechService: NSObject, ObservableObject {
    static let shared = SpeechService()
    
    @Published var isRecording = false
    @Published var transcribedText = ""
    @Published var recordingDuration = 0
    
    private var audioEngine = AVAudioEngine()
    private var speechRecognizer: SFSpeechRecognizer?
    private var recognitionRequest: SFSpeechAudioBufferRecognitionRequest?
    private var recognitionTask: SFSpeechRecognitionTask?
    private var timer: Timer?
    
    private var isSimulator: Bool {
        #if targetEnvironment(simulator)
        return true
        #else
        return false
        #endif
    }
    
    private var simulatedTexts = [
        "今天天气很好，我去公园散步了。",
        "工作完成了，感觉很有成就感。",
        "和朋友一起吃饭聊天，很开心。",
        "最近有点累，需要休息一下。",
        "学习了很多新知识，收获满满。"
    ]
    
    private override init() {
        super.init()
        if !isSimulator {
            speechRecognizer = SFSpeechRecognizer(locale: Locale(identifier: "zh-CN"))
        }
    }
    
    func requestAuthorization(completion: @escaping (Bool) -> Void) {
        if isSimulator {
            completion(true)
            return
        }
        
        SFSpeechRecognizer.requestAuthorization { authStatus in
            DispatchQueue.main.async {
                completion(authStatus == .authorized)
            }
        }
    }
    
    func startRecording(onTextChange: @escaping (String) -> Void) {
        if isSimulator {
            startSimulatedRecording(onTextChange: onTextChange)
            return
        }
        
        guard let speechRecognizer = speechRecognizer, speechRecognizer.isAvailable else {
            return
        }
        
        requestAuthorization { [weak self] authorized in
            guard let self = self, authorized else { return }
            
            self.createRecognitionRequest(onTextChange: onTextChange)
            
            self.audioEngine.prepare()
            do {
                try self.audioEngine.start()
            } catch {
                return
            }
            
            self.isRecording = true
            self.startDurationTimer()
        }
    }
    
    private func createRecognitionRequest(onTextChange: @escaping (String) -> Void) {
        recognitionRequest = SFSpeechAudioBufferRecognitionRequest()
        guard let recognitionRequest = recognitionRequest else {
            return
        }
        
        recognitionRequest.shouldReportPartialResults = true
        
        recognitionTask = speechRecognizer?.recognitionTask(with: recognitionRequest) { [weak self] result, error in
            guard let self = self else { return }
            
            if let result = result {
                self.transcribedText = result.bestTranscription.formattedString
                onTextChange(self.transcribedText)
            }
            
            if error != nil || result?.isFinal == true {
                self.audioEngine.stop()
                self.audioEngine.inputNode.removeTap(onBus: 0)
            }
        }
        
        let inputNode = audioEngine.inputNode
        let recordingFormat = inputNode.outputFormat(forBus: 0)
        
        inputNode.installTap(onBus: 0, bufferSize: 1024, format: recordingFormat) { [weak self] buffer, _ in
            self?.recognitionRequest?.append(buffer)
        }
    }
    
    private func startSimulatedRecording(onTextChange: @escaping (String) -> Void) {
        isRecording = true
        recordingDuration = 0
        transcribedText = ""
        
        timer = Timer.scheduledTimer(withTimeInterval: 2, repeats: true) { [weak self] _ in
            guard let self = self else { return }
            self.recordingDuration += 2
            let randomText = self.simulatedTexts.randomElement() ?? "模拟语音转写内容"
            self.transcribedText = randomText
            onTextChange(randomText)
        }
    }
    
    func stopRecording() -> String {
        timer?.invalidate()
        timer = nil
        
        if !isSimulator {
            audioEngine.stop()
            audioEngine.inputNode.removeTap(onBus: 0)
            recognitionRequest?.endAudio()
            recognitionTask?.cancel()
        }
        
        isRecording = false
        stopDurationTimer()
        
        let result = transcribedText
        transcribedText = ""
        return result
    }
    
    private func startDurationTimer() {
        recordingDuration = 0
        timer = Timer.scheduledTimer(withTimeInterval: 1, repeats: true) { [weak self] _ in
            guard let self = self else { return }
            self.recordingDuration += 1
        }
    }
    
    private func stopDurationTimer() {
        timer?.invalidate()
        timer = nil
    }
    
    func reset() {
        transcribedText = ""
        recordingDuration = 0
        isRecording = false
    }
}
