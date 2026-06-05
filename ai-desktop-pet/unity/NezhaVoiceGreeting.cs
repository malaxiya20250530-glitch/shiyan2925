using UnityEngine;
using UnityEngine.Networking;
using System.Collections;
using System.Collections.Generic;
using System.IO;
using System.Text;

/// <summary>
/// 灵绘语音系统 — TTS 合成 + 内置短语 + 在线语音
/// 支持：内置 PCM 短语 / Unity TTS / 在线 TTS API
/// </summary>
public class NezhaVoiceGreeting : MonoBehaviour
{
    [Header("音频源")]
    public AudioSource voiceSource;

    [Header("内置短语")]
    public List<VoicePhrase> phrases = new List<VoicePhrase>();

    [Header("TTS 设置")]
    public string ttsApiUrl = "";  // 留空则用程序化合成
    public float speechRate = 1f;
    public float volume = 1f;

    [Header("默认问候语")]
    [TextArea(2, 4)]
    public string greetingText = "你好，我是灵绘，可以唱歌跳舞的！";
    public string idleText = "想听什么歌？";
    public string downloadText = "正在下载歌曲，请稍等";
    public string errorText = "哎呀，出错了";

    private Queue<SpeakTask> _taskQueue = new Queue<SpeakTask>();
    private bool _isSpeaking;

    [System.Serializable]
    public class VoicePhrase
    {
        public string key;       // 触发词
        public string text;      // 文本
        public AudioClip clip;   // 预置音频
    }

    class SpeakTask
    {
        public string text;
        public System.Action onComplete;
    }

    void Start()
    {
        if (voiceSource == null)
            voiceSource = gameObject.AddComponent<AudioSource>();
        voiceSource.playOnAwake = false;
        voiceSource.loop = false;

        InitPhrases();
    }

    void InitPhrases()
    {
        phrases = new List<VoicePhrase>
        {
            new VoicePhrase { key = "greeting", text = greetingText },
            new VoicePhrase { key = "idle", text = idleText },
            new VoicePhrase { key = "download", text = downloadText },
            new VoicePhrase { key = "error", text = errorText },
            new VoicePhrase { key = "play", text = "好的，马上播放" },
            new VoicePhrase { key = "next", text = "下一首" },
            new VoicePhrase { key = "hello", text = "你好呀，我是灵绘" },
            new VoicePhrase { key = "dance", text = "看我的舞姿！" },
            new VoicePhrase { key = "fired_up", text = "燃烧吧！" },
        };
    }

    /// <summary>说一句话（加入队列）</summary>
    public void Speak(string text, System.Action onComplete = null)
    {
        if (string.IsNullOrEmpty(text)) return;

        _taskQueue.Enqueue(new SpeakTask { text = text, onComplete = onComplete });
        if (!_isSpeaking)
            StartCoroutine(ProcessQueue());
    }

    /// <summary>按 key 说预设短语</summary>
    public void SpeakByKey(string key, System.Action onComplete = null)
    {
        var phrase = phrases.Find(p => p.key == key);
        if (phrase != null)
            Speak(phrase.text, onComplete);
    }

    IEnumerator ProcessQueue()
    {
        _isSpeaking = true;

        while (_taskQueue.Count > 0)
        {
            var task = _taskQueue.Dequeue();

            // 查找预置音频
            var phrase = phrases.Find(p => p.text == task.text);
            if (phrase != null && phrase.clip != null)
            {
                voiceSource.clip = phrase.clip;
                voiceSource.Play();
                yield return new WaitForSeconds(phrase.clip.length);
            }
            else
            {
                // 程序化 TTS 合成
                yield return SynthesizeSpeech(task.text);
            }

            task.onComplete?.Invoke();
        }

        _isSpeaking = false;
    }

    /// <summary>程序化语音合成（简易波形合成）</summary>
    IEnumerator SynthesizeSpeech(string text)
    {
        // 优先用在线 TTS
        if (!string.IsNullOrEmpty(ttsApiUrl))
        {
            yield return OnlineTTS(text);
            yield break;
        }

        // 本地简易合成 — 生成提示音 + 字幕显示
        float duration = text.Length * 0.15f / speechRate;
        AudioClip beepClip = GenerateToneAndClip(text, duration);
        if (beepClip != null)
        {
            voiceSource.clip = beepClip;
            voiceSource.volume = volume * 0.3f;
            voiceSource.Play();
            yield return new WaitForSeconds(duration);
        }
    }

    /// <summary>在线 TTS 调用</summary>
    IEnumerator OnlineTTS(string text)
    {
        string url = ttsApiUrl.Replace("{TEXT}", UnityWebRequest.EscapeURL(text));

        using (var req = UnityWebRequestMultimedia.GetAudioClip(url, AudioType.MPEG))
        {
            req.timeout = 10;
            yield return req.SendWebRequest();

            if (req.result == UnityWebRequest.Result.Success)
            {
                var clip = DownloadHandlerAudioClip.GetContent(req);
                voiceSource.clip = clip;
                voiceSource.Play();
                yield return new WaitForSeconds(clip.length);
            }
            else
            {
                // 降级到本地合成
                yield return SynthesizeLocal(text);
            }
        }
    }

    /// <summary>本地简易合成</summary>
    IEnumerator SynthesizeLocal(string text)
    {
        float duration = Mathf.Max(text.Length * 0.12f, 0.5f);
        AudioClip clip = GenerateToneAndClip(text, duration);
        if (clip != null)
        {
            voiceSource.clip = clip;
            voiceSource.volume = volume * 0.25f;
            voiceSource.Play();
            yield return new WaitForSeconds(duration);
        }
    }

    /// <summary>生成提示音波形</summary>
    AudioClip GenerateToneAndClip(string text, float duration)
    {
        int sampleRate = 22050;
        int samples = Mathf.CeilToInt(duration * sampleRate);
        var clip = AudioClip.Create("tts_" + text.GetHashCode(), samples, 1, sampleRate, false);

        float[] data = new float[samples];
        float baseFreq = 180 + Mathf.Sin(text.Length * 0.5f) * 60; // 不同长度不同音高

        for (int i = 0; i < samples; i++)
        {
            float t = (float)i / sampleRate;
            float envelope = Mathf.Min(1, (1 - t / duration) * 3);

            // 简单和弦
            float wave = Mathf.Sin(t * baseFreq * Mathf.PI * 2) * 0.5f;
            wave += Mathf.Sin(t * baseFreq * 1.5f * Mathf.PI * 2) * 0.3f;
            wave += Mathf.Sin(t * baseFreq * 2f * Mathf.PI * 2) * 0.15f;

            // 音调变化（模拟语调）
            float pitchShift = 1 + Mathf.Sin(t * 3f) * 0.15f + Mathf.Cos(t * 7f) * 0.1f;
            wave = Mathf.Sin(t * baseFreq * pitchShift * Mathf.PI * 2) * envelope;

            data[i] = wave * 0.4f;
        }

        clip.SetData(data, 0);
        return clip;
    }

    /// <summary>停止说话</summary>
    public void StopSpeaking()
    {
        _taskQueue.Clear();
        voiceSource.Stop();
        _isSpeaking = false;
    }
}
