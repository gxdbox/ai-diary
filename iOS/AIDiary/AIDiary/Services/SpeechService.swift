import Foundation
import Speech
import AVFoundation
import Combine

class SpeechService: NSObject, ObservableObject {
    static let shared = SpeechService()

    @Published var isRecording = false
    @Published var transcribedText = ""
    @Published var recordingDuration = 0
    @Published var audioLevel: Float = 0
    @Published var isPaused = false
    @Published var realtimeASRText: String = ""  // 实时云端 ASR 结果

    private var audioEngine = AVAudioEngine()
    private var speechRecognizer: SFSpeechRecognizer?
    private var recognitionRequest: SFSpeechAudioBufferRecognitionRequest?
    private var recognitionTask: SFSpeechRecognitionTask?
    private var timer: Timer?
    private var levelTimer: Timer?
    private var pausedText: String = ""
    private var audioRecorder: AVAudioRecorder?
    private var recordedAudioURL: URL?
    private var isTapInstalled = false

    // 实时标点：静音检测
    private var silenceStartTime: Date?
    private var punctuationTimer: Timer?
    private let silenceThreshold: Float = 0.01

    // 实时云端 ASR (WebSocket → DashScope)
    private var asrWebSocket: URLSessionWebSocketTask?
    private var asrWebSocketSession: URLSession?
    private var asrAudioConverter: AVAudioConverter?
    private var asrOutputFormat: AVAudioFormat?
    private var isASRConnected = false

    // 音频发送缓冲：累积到约 100ms（DashScope 建议每包 1KB~16KB）
    private var asrAudioBuffer = Data()
    private let asrChunkSize = 3200  // 100ms @ 16kHz Int16 mono = 3200 bytes

    // 实时 ASR 句子累积：DashScope 按句子返回，需自行拼接
    private var finalizedSentences: [String] = []  // 已完成识别的句子
    private var currentSentenceText: String = ""  // 当前正在识别的句子（临时）

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

    // MARK: - 实时云端 ASR

    /// 建立 WebSocket 连接到后端实时 ASR 服务
    func connectRealtimeASR() {
        guard let token = KeychainService.shared.loadToken(),
              let baseURL = URL(string: AppConfig.baseURL),
              let host = baseURL.host else { return }

        let scheme = baseURL.scheme == "https" ? "wss" : "ws"
        let port = baseURL.port.map { ":\($0)" } ?? ""
        guard let wsURL = URL(string: "\(scheme)://\(host)\(port)/ws/asr?token=\(token)") else { return }

        let session = URLSession(configuration: .default)
        asrWebSocketSession = session
        asrWebSocket = session.webSocketTask(with: wsURL)
        asrWebSocket?.resume()
        receiveASRReady()
    }

    private func receiveASRReady() {
        asrWebSocket?.receive { [weak self] result in
            guard case .success(let message) = result,
                  case .string(let text) = message,
                  let data = text.data(using: .utf8),
                  let json = try? JSONSerialization.jsonObject(with: data) as? [String: Any],
                  json["type"] as? String == "ready" else {
                return
            }
            self?.isASRConnected = true
            DispatchQueue.main.async {
                self?.realtimeASRText = ""
                self?.finalizedSentences = []
                self?.currentSentenceText = ""
            }
            self?.startReceivingASRResults()
        }
    }

    private func startReceivingASRResults() {
        receiveNextASRResult()
    }

    private func receiveNextASRResult() {
        asrWebSocket?.receive { [weak self] result in
            guard let self = self else { return }
            switch result {
            case .success(let message):
                if case .string(let text) = message,
                   let data = text.data(using: .utf8),
                   let json = try? JSONSerialization.jsonObject(with: data) as? [String: Any],
                   let asrText = json["text"] as? String {
                    let sentenceEnd = json["sentence_end"] as? Bool ?? false
                    DispatchQueue.main.async {
                        if sentenceEnd {
                            // 句子识别完成，加入已完成列表
                            if !asrText.isEmpty {
                                self.finalizedSentences.append(asrText)
                            }
                            self.currentSentenceText = ""
                        } else {
                            // 句子识别中，更新当前句子的临时文本
                            self.currentSentenceText = asrText
                        }
                        // 完整文本 = 已完成句子 + 当前进行中的句子
                        self.realtimeASRText = self.finalizedSentences.joined() + self.currentSentenceText
                    }
                }
                self.receiveNextASRResult()
            case .failure:
                self.isASRConnected = false
            }
        }
    }

    /// 断开实时 ASR 连接
    func disconnectRealtimeASR() {
        isASRConnected = false
        // flush 缓冲区剩余音频，避免最后几个字丢失
        if !asrAudioBuffer.isEmpty, let ws = asrWebSocket {
            ws.send(.data(asrAudioBuffer)) { _ in }
            asrAudioBuffer.removeAll(keepingCapacity: true)
        }
        asrWebSocket?.cancel(with: .normalClosure, reason: nil)
        asrWebSocket = nil
        asrWebSocketSession = nil
        asrAudioConverter = nil
    }

    /// 设置音频格式转换器（输入格式 → 16kHz PCM Int16）
    func setupASRAudioConverter(inputFormat: AVAudioFormat) {
        guard let outputFormat = AVAudioFormat(
            commonFormat: .pcmFormatInt16,
            sampleRate: 16000,
            channels: 1,
            interleaved: false
        ) else { return }
        asrOutputFormat = outputFormat
        asrAudioConverter = AVAudioConverter(from: inputFormat, to: outputFormat)
    }

    /// 将音频 buffer 转换为 16kHz PCM 并发送到云端 ASR
    func sendAudioToRealtimeASR(buffer: AVAudioPCMBuffer) {
        guard isASRConnected,
              let ws = asrWebSocket,
              let converter = asrAudioConverter,
              let outputFormat = asrOutputFormat else { return }

        let ratio = 16000.0 / buffer.format.sampleRate
        let outputFrameCapacity = AVAudioFrameCount(Double(buffer.frameLength) * ratio)
        guard let outputBuffer = AVAudioPCMBuffer(
            pcmFormat: outputFormat,
            frameCapacity: max(1, outputFrameCapacity)
        ) else { return }

        var error: NSError?
        let inputBlock: AVAudioConverterInputBlock = { _, outStatus in
            outStatus.pointee = .haveData
            return buffer
        }
        converter.convert(to: outputBuffer, error: &error, withInputFrom: inputBlock)

        // 只在有实际输出数据时处理
        guard error == nil, outputBuffer.frameLength > 0,
              let int16Data = outputBuffer.int16ChannelData else { return }

        let byteCount = Int(outputBuffer.frameLength) * MemoryLayout<Int16>.size
        let data = Data(bytes: int16Data[0], count: byteCount)

        // 累积音频数据，达到约 100ms 后发送（DashScope 建议每包 1KB~16KB）
        asrAudioBuffer.append(data)
        if asrAudioBuffer.count >= asrChunkSize {
            ws.send(.data(asrAudioBuffer)) { _ in }
            asrAudioBuffer.removeAll(keepingCapacity: true)
        }
    }

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

    /// 安全移除 inputNode tap，不论引擎是否运行
    private func safeRemoveTap() {
        guard isTapInstalled else { return }
        isTapInstalled = false
        audioEngine.inputNode.removeTap(onBus: 0)
    }

    /// 清理引擎状态：取消旧 task、移除旧 tap、停止引擎
    private func cleanupEngineState() {
        guard !isSimulator else { return }

        recognitionTask?.cancel()
        recognitionTask = nil
        recognitionRequest?.endAudio()
        recognitionRequest = nil
        safeRemoveTap()
        audioEngine.stop()
        // 停用录音音频会话，让播放时可以干净地重新配置
        try? AVAudioSession.sharedInstance().setActive(false, options: .notifyOthersOnDeactivation)
    }

    func startRecording(onTextChange: @escaping (String) -> Void) {
        if isSimulator {
            cleanupEngineState()
            startSimulatedRecording(onTextChange: onTextChange)
            startAudioRecorder()
            return
        }

        guard let speechRecognizer = speechRecognizer, speechRecognizer.isAvailable else {
            return
        }

        requestAuthorization { [weak self] authorized in
            guard let self = self, authorized else { return }

            // 清理上次录音残留状态（取消旧 task、移除旧 tap）
            self.cleanupEngineState()

            // 重建 audioEngine 确保干净状态
            self.audioEngine = AVAudioEngine()

            guard self.setupAudioSession() else {
                print("SpeechService: 音频会话配置失败")
                return
            }

            self.startAudioRecorder()
            self.createRecognitionRequest(onTextChange: onTextChange)

            self.audioEngine.prepare()
            do {
                try self.audioEngine.start()
            } catch {
                print("SpeechService: audioEngine 启动失败: \(error)")
                self.cleanupEngineState()
                return
            }

            self.isRecording = true
            self.startDurationTimer()
            self.startPunctuationTimer()

            // 启动实时云端 ASR
            self.connectRealtimeASR()
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
                self.transcribedText = self.buildTextWithPunctuation(from: result.bestTranscription)
                onTextChange(self.transcribedText)
            }
            // 注意：这里绝不调用 stop/removeTap
            // 所有清理由 stopRecording() 统一处理
            // 这样才能避免与 stopRecording() 的 race condition 导致崩溃
        }

        let inputNode = audioEngine.inputNode
        let recordingFormat = inputNode.outputFormat(forBus: 0)

        inputNode.installTap(onBus: 0, bufferSize: 1024, format: recordingFormat) { [weak self] buffer, _ in
            self?.recognitionRequest?.append(buffer)

            guard let channelData = buffer.floatChannelData else { return }
            let channelDataValue = channelData[0]
            let channelLength = Int(buffer.frameLength)

            var sum: Float = 0
            for i in 0..<channelLength {
                sum += channelDataValue[i] * channelDataValue[i]
            }
            let rms = sqrt(sum / Float(channelLength))
            let level = min(max((rms * 50), 0), 1)

            DispatchQueue.main.async {
                self?.audioLevel = level
            }

            // 发送音频到实时云端 ASR
            self?.sendAudioToRealtimeASR(buffer: buffer)
        }

        // 设置音频格式转换器（用于云端 ASR）
        setupASRAudioConverter(inputFormat: recordingFormat)
        isTapInstalled = true
    }

    /// 根据 ASR segment 间隙自动插入标点
    /// 间隙 > 0.5s → 逗号，> 1.5s → 句号
    private func buildTextWithPunctuation(from transcription: SFTranscription) -> String {
        let segments = transcription.segments
        guard !segments.isEmpty else { return transcription.formattedString }

        var text = ""
        for (index, segment) in segments.enumerated() {
            if index > 0 {
                let prev = segments[index - 1]
                let prevEnd = prev.timestamp + prev.duration
                let gap = segment.timestamp - prevEnd
                if gap > 1.5 {
                    text += "。"
                } else if gap > 0.5 {
                    text += "，"
                }
            }
            text += segment.substring
        }
        return text.isEmpty ? transcription.formattedString : text
    }

    // MARK: - 实时标点（静音检测）

    private func startPunctuationTimer() {
        punctuationTimer = Timer.scheduledTimer(withTimeInterval: 0.5, repeats: true) { [weak self] _ in
            self?.checkTrailingSilence()
        }
    }

    private func stopPunctuationTimer() {
        punctuationTimer?.invalidate()
        punctuationTimer = nil
        silenceStartTime = nil
    }

    /// 检测录音尾部的静音段，自动追加标点
    private func checkTrailingSilence() {
        guard isRecording, !isPaused, !transcribedText.isEmpty else { return }

        // 已有尾标点则跳过
        let lastChar = transcribedText.last
        if lastChar == "。" || lastChar == "，" || lastChar == "？" || lastChar == "！" {
            return
        }

        if audioLevel < silenceThreshold {
            if silenceStartTime == nil {
                silenceStartTime = Date()
            }
            let silenceDuration = Date().timeIntervalSince(silenceStartTime!)
            if silenceDuration > 1.5 {
                transcribedText += "。"
            } else if silenceDuration > 0.5 {
                transcribedText += "，"
            }
        } else {
            silenceStartTime = nil
        }
    }

    func pauseRecording() {
        guard isRecording, !isPaused else { return }
        isPaused = true
        pausedText = transcribedText
        timer?.invalidate()
        levelTimer?.invalidate()
        punctuationTimer?.invalidate()

        if !isSimulator {
            audioEngine.pause()
        }
    }

    func resumeRecording(onTextChange: @escaping (String) -> Void) {
        guard isPaused else { return }
        isPaused = false
        transcribedText = pausedText

        if isSimulator {
            startSimulatedRecording(onTextChange: onTextChange)
        } else {
            do {
                try audioEngine.start()
                startDurationTimer()
                startLevelTimer()
                startPunctuationTimer()
            } catch {
                print("SpeechService: 恢复录音失败: \(error)")
                isPaused = true
            }
        }
    }

    func clearText() {
        transcribedText = ""
        pausedText = ""
        realtimeASRText = ""
        finalizedSentences = []
        currentSentenceText = ""
        recordingDuration = 0
        silenceStartTime = nil
    }

    private func startLevelTimer() {}

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
        startPunctuationTimer()

        timer = Timer.scheduledTimer(withTimeInterval: 2, repeats: true) { [weak self] _ in
            guard let self = self, !self.isPaused else { return }
            self.recordingDuration += 2
            let randomText = self.simulatedTexts.randomElement() ?? "模拟语音转写内容"
            self.transcribedText += randomText
            onTextChange(self.transcribedText)
        }

        levelTimer = Timer.scheduledTimer(withTimeInterval: 0.1, repeats: true) { [weak self] _ in
            guard let self = self, !self.isPaused else { return }
            let level = Float.random(in: 0.2...0.8)
            self.audioLevel = level
        }
    }

    func stopRecording() -> String {
        timer?.invalidate()
        timer = nil
        levelTimer?.invalidate()
        levelTimer = nil
        stopPunctuationTimer()

        audioRecorder?.stop()
        audioRecorder = nil

        // 先取消 task（nil 引用防止回调操作 engine），再清理引擎
        let task = recognitionTask
        recognitionTask = nil
        let request = recognitionRequest
        recognitionRequest = nil
        task?.cancel()
        request?.endAudio()

        safeRemoveTap()
        audioEngine.stop()

        isRecording = false
        isPaused = false
        stopDurationTimer()
        stopLevelTimer()
        disconnectRealtimeASR()

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

    // MARK: - Audio Recorder

    func getRecordedAudioURL() -> URL? {
        return recordedAudioURL
    }

    private func setupAudioSession() -> Bool {
        let session = AVAudioSession.sharedInstance()
        do {
            try session.setCategory(.playAndRecord, mode: .default, options: [.defaultToSpeaker])
            try session.setActive(true)
            return true
        } catch {
            print("SpeechService: AVAudioSession 配置失败: \(error)")
            return false
        }
    }

    private func startAudioRecorder() {
        let tempDir = FileManager.default.temporaryDirectory
        let fileName = "diary_recording_\(UUID().uuidString).m4a"
        let fileURL = tempDir.appendingPathComponent(fileName)

        let settings: [String: Any] = [
            AVFormatIDKey: Int(kAudioFormatMPEG4AAC),
            AVSampleRateKey: 44100.0,
            AVNumberOfChannelsKey: 1,
            AVEncoderAudioQualityKey: AVAudioQuality.high.rawValue,
            AVEncoderBitRateKey: 128000
        ]

        recordedAudioURL = fileURL
        do {
            audioRecorder = try AVAudioRecorder(url: fileURL, settings: settings)
            audioRecorder?.record()
        } catch {
            print("SpeechService: AVAudioRecorder 初始化失败: \(error)")
            audioRecorder = nil
            recordedAudioURL = nil
        }
    }

    func reset() {
        cleanupEngineState()
        stopPunctuationTimer()
        disconnectRealtimeASR()
        transcribedText = ""
        pausedText = ""
        realtimeASRText = ""
        finalizedSentences = []
        currentSentenceText = ""
        recordingDuration = 0
        audioLevel = 0
        isRecording = false
        isPaused = false
        recordedAudioURL = nil
        audioRecorder = nil
        silenceStartTime = nil
    }
}
