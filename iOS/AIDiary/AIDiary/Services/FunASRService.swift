import Foundation
import AVFoundation
import Combine
import UIKit

/// Fun-ASR iOS SDK 实时语音识别服务
///
/// 封装 DashScope Fun-ASR iOS SDK（nuisdk.framework），
/// 直连 DashScope 服务，无需后端 WebSocket 中转。
///
/// 架构：AVAudioEngine tap → Int16 PCM buffer → SDK onNuiNeedAudioData → DashScope
///
/// SDK 文档: https://help.aliyun.com/zh/model-studio/ios-sdk-for-fun-asr-real-time-service
class FunASRService: NSObject, ObservableObject {

    static let shared = FunASRService()

    // MARK: - Published State

    /// 实时识别文本（已完成句子 + 当前句子）
    @Published var realtimeText: String = ""
    /// SDK 是否已连接并正在识别
    @Published var isRecognizing = false
    /// 连接错误信息
    @Published var connectionError: String?

    // MARK: - SDK Instance

    private var nui: NeoNui?
    private var isInitialized = false

    // MARK: - Sentence Accumulation

    private var finalizedSentences: [String] = []
    private var currentSentenceText: String = ""

    // MARK: - Audio Buffer (thread-safe)

    /// SDK 通过 onNuiNeedAudioData 拉取音频，tap 回调推送音频，需线程安全缓冲
    private var audioBuffer = Data()
    private let bufferLock = NSLock()

    // MARK: - Configuration

    private var apiKey: String = ""
    private var wsURL: String = "wss://dashscope.aliyuncs.com/api-ws/v1/inference"
    private var model: String = "fun-asr-realtime"
    private var nativeSampleRate: Double = 16000

    // MARK: - Lifecycle

    private override init() {
        super.init()
    }

    /// 从后端获取 SDK 配置（API Key 等），必须在 startRecognition 前调用
    func fetchConfig() async -> Bool {
        do {
            let config = try await APIService.shared.fetchASRSdkConfig()
            self.apiKey = config.apiKey
            self.wsURL = config.wsURL
            self.model = config.model
            return true
        } catch {
            print("FunASRService: 获取 SDK 配置失败: \(error)")
            return false
        }
    }

    // MARK: - Start / Stop

    /// 启动实时识别
    func startRecognition(sampleRate: Double) {
        guard !isRecognizing else { return }
        self.nativeSampleRate = sampleRate

        // 清空状态
        finalizedSentences = []
        currentSentenceText = ""
        bufferLock.lock()
        audioBuffer.removeAll(keepingCapacity: true)
        bufferLock.unlock()

        DispatchQueue.main.async {
            self.realtimeText = ""
        }

        // 初始化 SDK（单例，仅首次）
        if !isInitialized {
            guard initializeSDK() else {
                print("FunASRService: SDK 初始化失败")
                return
            }
        }

        // 设置识别参数
        configureRecognition()

        // 启动识别
        let ret = nui?.nui_dialog_start(MODE_P2T, dialogParam: nil)
        if let ret = ret, ret != SUCCESS {
            print("FunASRService: 启动识别失败, code=\(ret)")
            DispatchQueue.main.async {
                self.connectionError = "ASR 启动失败(\(ret))"
            }
            return
        }

        DispatchQueue.main.async {
            self.isRecognizing = true
            self.connectionError = nil
        }
    }

    /// 停止识别（等待最终结果）
    func stopRecognition() {
        guard isRecognizing else { return }
        // force=false: 等待服务端返回最终识别结果
        nui?.nui_dialog_cancel(false)
        // EVENT_TRANSCRIBER_COMPLETE 回调中会设置 isRecognizing = false
    }

    /// 释放 SDK 资源（App 退出或不再使用时调用）
    func release() {
        nui?.nui_release()
        nui = nil
        isInitialized = false
        DispatchQueue.main.async {
            self.isRecognizing = false
        }
    }

    // MARK: - Audio Feed (from SpeechService tap)

    /// 接收来自 AVAudioEngine tap 的音频数据（Float32 → Int16 PCM）
    /// 由 SpeechService 的 tap 回调调用
    func feedAudioBuffer(_ buffer: AVAudioPCMBuffer) {
        guard isRecognizing,
              let channelData = buffer.floatChannelData else { return }

        let frameLength = Int(buffer.frameLength)
        let floatPtr = channelData[0]

        // Float32 → Int16 PCM（保留原生采样率，不做降采样）
        var int16Samples = [Int16](repeating: 0, count: frameLength)
        for i in 0..<frameLength {
            let sample = floatPtr[i]
            // Clamp to [-1.0, 1.0] then scale to Int16 range
            let clamped = max(-1.0, min(1.0, sample))
            int16Samples[i] = Int16(clamped * 32767.0)
        }

        let data = Data(bytes: int16Samples, count: frameLength * MemoryLayout<Int16>.size)

        bufferLock.lock()
        audioBuffer.append(data)
        bufferLock.unlock()
    }

    // MARK: - SDK Initialization

    private func initializeSDK() -> Bool {
        guard !apiKey.isEmpty else {
            print("FunASRService: API Key 为空，请先调用 fetchConfig()")
            return false
        }

        nui = NeoNui()
        guard let nui = nui else { return false }

        // 连接与控制参数
        let params: [String: Any] = [
            "url": wsURL,
            "apikey": apiKey,
            "device_id": UIDevice.current.identifierForVendor?.uuidString ?? "ai_diary_ios",
            "service_mode": "1"  // 实时语音识别固定为 "1"
        ]

        guard let jsonData = try? JSONSerialization.data(withJSONObject: params),
              let jsonString = String(data: jsonData, encoding: .utf8) else {
            return false
        }

        let ret = nui.nui_initialize(jsonString, logLevel: NUI_LOG_LEVEL_WARNING, saveLog: false)
        guard ret == SUCCESS else {
            print("FunASRService: nui_initialize 失败, code=\(ret)")
            return false
        }

        // 设置 delegate
        nui.delegate = self
        isInitialized = true
        return true
    }

    private func configureRecognition() {
        // 语音识别效果参数
        let nlsConfig: [String: Any] = [
            "model": model,
            "sr_format": "pcm",
            "sample_rate": Int(nativeSampleRate),
            "semantic_punctuation_enabled": true,  // 语义断句（准确度更高）
            "language_hints": ["zh"],
            "heartbeat": true,  // 保持长连接
            "parameters": [
                "speech_noise_threshold": 0.0
            ]
        ]

        let params: [String: Any] = [
            "service_type": 4,  // 实时语音识别固定为 4
            "nls_config": nlsConfig
        ]

        guard let jsonData = try? JSONSerialization.data(withJSONObject: params),
              let jsonString = String(data: jsonData, encoding: .utf8) else {
            return
        }

        nui?.nui_set_params(jsonString)
    }

    // MARK: - Text Assembly

    private func updateRealtimeText() {
        let text = finalizedSentences.joined() + currentSentenceText
        DispatchQueue.main.async {
            self.realtimeText = text
        }
    }

    /// 获取当前完整识别文本（供 saveDiary 使用）
    func getFinalText() -> String {
        return finalizedSentences.joined() + currentSentenceText
    }

    /// 重置文本状态
    func resetText() {
        finalizedSentences = []
        currentSentenceText = ""
        DispatchQueue.main.async {
            self.realtimeText = ""
        }
    }
}

// MARK: - NeoNuiSdkDelegate

extension FunASRService: NeoNuiSdkDelegate {

    /// SDK 事件回调：识别结果、错误、完成等
    func onNuiEventCallback(_ nuiEvent: NuiCallbackEvent,
                            dialog: Int,
                            kwsResult wuw: UnsafePointer<CChar>!,
                            asrResult asr_result: UnsafePointer<CChar>!,
                            ifFinish finish: Bool,
                            retCode code: Int32) {

        switch nuiEvent {
        case EVENT_TRANSCRIBER_STARTED:
            print("FunASRService: 识别任务已启动")

        case EVENT_ASR_PARTIAL_RESULT:
            // 中间结果：更新当前句子文本
            if let result = parseASRResult(asr_result) {
                DispatchQueue.main.async {
                    self.currentSentenceText = result
                    self.updateRealtimeText()
                }
            }

        case EVENT_SENTENCE_END:
            // 一句话结束：加入已完成列表
            if let result = parseASRResult(asr_result), !result.isEmpty {
                DispatchQueue.main.async {
                    self.finalizedSentences.append(result)
                    self.currentSentenceText = ""
                    self.updateRealtimeText()
                }
            } else {
                DispatchQueue.main.async {
                    self.currentSentenceText = ""
                    self.updateRealtimeText()
                }
            }

        case EVENT_TRANSCRIBER_COMPLETE:
            // 识别完全结束
            DispatchQueue.main.async {
                self.isRecognizing = false
            }
            print("FunASRService: 识别完成")

        case EVENT_ASR_ERROR:
            print("FunASRService: ASR 错误, code=\(code)")
            DispatchQueue.main.async {
                self.isRecognizing = false
                if code == 240093 {
                    self.connectionError = "云端 ASR 连接超时，请检查网络后重试"
                } else {
                    self.connectionError = "云端 ASR 错误(\(code))"
                }
            }

        case EVENT_MIC_ERROR:
            print("FunASRService: 麦克风错误（2秒未收到音频数据）")

        default:
            break
        }
    }

    /// SDK 音频状态回调：通知何时开始/停止录音
    func onNuiAudioStateChanged(_ state: NuiAudioState) {
        switch state {
        case STATE_OPEN:
            print("FunASRService: 音频状态 → OPEN")
        case STATE_PAUSE:
            print("FunASRService: 音频状态 → PAUSE")
        case STATE_CLOSE:
            print("FunASRService: 音频状态 → CLOSE")
        default:
            break
        }
    }

    /// SDK 拉取音频数据回调（SDK 内部线程调用）
    func onNuiNeedAudioData(_ audioData: UnsafeMutablePointer<CChar>!, length len: Int32) -> Int32 {
        bufferLock.lock()
        defer { bufferLock.unlock() }

        let bytesToCopy = min(Int(len), audioBuffer.count)
        guard bytesToCopy > 0 else { return 0 }

        audioBuffer.withUnsafeBytes { ptr in
            if let baseAddress = ptr.baseAddress {
                memcpy(audioData, baseAddress, bytesToCopy)
            }
        }
        audioBuffer.removeFirst(bytesToCopy)
        return Int32(bytesToCopy)
    }

    /// SDK 日志回调
    func onNuiLogTrackCallback(_ level: NuiSdkLogLevel, logMessage log: UnsafePointer<CChar>!) {
        // 仅打印警告及以上级别
        if level.rawValue >= NUI_LOG_LEVEL_WARNING.rawValue {
            let message = String(cString: log)
            print("FunASRService [SDK]: \(message)")
        }
    }

    // MARK: - Helpers

    /// 解析 ASR 结果 JSON，提取 text 字段
    private func parseASRResult(_ asrResult: UnsafePointer<CChar>!) -> String? {
        guard let asrResult = asrResult else { return nil }
        let jsonString = String(cString: asrResult)
        guard let data = jsonString.data(using: .utf8),
              let json = try? JSONSerialization.jsonObject(with: data) as? [String: Any] else {
            return nil
        }

        // SDK 返回格式: {"text": "识别文本", ...} 或嵌套在 payload 中
        if let text = json["text"] as? String {
            return text
        }
        // 兼容: payload.result.text
        if let payload = json["payload"] as? [String: Any],
           let result = payload["result"] as? [String: Any],
           let text = result["text"] as? String {
            return text
        }
        return nil
    }
}
