import Foundation
import Speech
import AVFoundation
import Combine

class SpeechService: NSObject, ObservableObject {
    static let shared = SpeechService()

    @Published var isRecording = false
    @Published var transcribedText = ""
    @Published var recordingDuration = 0
    @Published var audioLevel: Float = 0  // 音量级别 (0-1)
    @Published var isPaused = false

    private var audioEngine = AVAudioEngine()
    private var speechRecognizer: SFSpeechRecognizer?
    private var recognitionRequest: SFSpeechAudioBufferRecognitionRequest?
    private var recognitionTask: SFSpeechRecognitionTask?
    private var timer: Timer?
    private var levelTimer: Timer?
    private var pausedText: String = ""  // 暂停时保存的文本
    
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

            // 计算音量
            guard let channelData = buffer.floatChannelData else { return }
            let channelDataValue = channelData[0]
            let channelLength = Int(buffer.frameLength)

            // 计算 RMS 值
            var sum: Float = 0
            for i in 0..<channelLength {
                sum += channelDataValue[i] * channelDataValue[i]
            }
            let rms = sqrt(sum / Float(channelLength))

            // 转换为 0-1 范围，并添加适当的缩放
            let level = min(max((rms * 50), 0), 1)

            DispatchQueue.main.async {
                self?.audioLevel = level
            }
        }
    }

    func pauseRecording() {
        if isRecording && !isPaused {
            isPaused = true
            pausedText = transcribedText
            timer?.invalidate()
            levelTimer?.invalidate()

            if !isSimulator {
                audioEngine.pause()
            }
        }
    }

    func resumeRecording(onTextChange: @escaping (String) -> Void) {
        if isPaused {
            isPaused = false
            transcribedText = pausedText

            if isSimulator {
                startSimulatedRecording(onTextChange: onTextChange)
            } else {
                try? audioEngine.start()
                startDurationTimer()
                startLevelTimer()
            }
        }
    }

    func clearText() {
        transcribedText = ""
        pausedText = ""
        recordingDuration = 0
    }

    private func startLevelTimer() {
        // 音量监测通过 audio tap 实现
    }

    private func stopLevelTimer() {
        levelTimer?.invalidate()
        levelTimer = nil
        audioLevel = 0
    }
    
    private func startSimulatedRecording(onTextChange: @escaping (String) -> Void) {
        isRecording = true
        isPaused = false
        recordingDuration = 0
        transcribedText = pausedText

        timer = Timer.scheduledTimer(withTimeInterval: 2, repeats: true) { [weak self] _ in
            guard let self = self, !self.isPaused else { return }
            self.recordingDuration += 2
            let randomText = self.simulatedTexts.randomElement() ?? "模拟语音转写内容"
            self.transcribedText += randomText
            onTextChange(self.transcribedText)
        }

        // 模拟音量变化
        levelTimer = Timer.scheduledTimer(withTimeInterval: 0.1, repeats: true) { [weak self] _ in
            guard let self = self, !self.isPaused else { return }
            // 随机生成音量，模拟说话时的变化
            let level = Float.random(in: 0.2...0.8)
            self.audioLevel = level
        }
    }
    
    func stopRecording() -> String {
        timer?.invalidate()
        timer = nil
        levelTimer?.invalidate()
        levelTimer = nil

        if !isSimulator {
            audioEngine.stop()
            audioEngine.inputNode.removeTap(onBus: 0)
            recognitionRequest?.endAudio()
            recognitionTask?.cancel()
        }

        isRecording = false
        isPaused = false
        stopDurationTimer()
        stopLevelTimer()

        let result = transcribedText
        transcribedText = ""
        pausedText = ""
        return result
    }
    
    private func startDurationTimer() {
        recordingDuration = 0
        timer = Timer.scheduledTimer(withTimeInterval: 1, repeats: true) { [weak self] _ in
            guard let self = self, !self.isPaused else { return }
            self.recordingDuration += 1
        }
        startLevelTimer()
    }

    private func stopDurationTimer() {
        timer?.invalidate()
        timer = nil
    }

    func reset() {
        transcribedText = ""
        pausedText = ""
        recordingDuration = 0
        audioLevel = 0
        isRecording = false
        isPaused = false
    }
}
