using UnityEngine;
using UnityEngine.Networking;
using System.Collections;
using System.Collections.Generic;
using System.IO;

/// <summary>
/// 灵绘音乐播放器 — 内置歌单 + 网络下载 + BPM同步舞蹈
/// </summary>
public class NezhaMusicPlayer : MonoBehaviour
{
    [Header("音频源")]
    public AudioSource musicSource;   // 音乐
    public AudioSource voiceSource;   // 语音提示

    [Header("内置歌单")]
    public List<SongInfo> builtInSongs = new List<SongInfo>();

    [Header("组件联动")]
    public NezhaDancer dancer;
    public NezhaVoiceGreeting voiceGreeting;

    [Header("状态")]
    public bool isPlaying;
    public SongInfo currentSong;
    public float currentBPM = 120f;

    private int _currentIndex = -1;
    private string _downloadDir;

    // ── 歌单数据结构 ──
    [System.Serializable]
    public class SongInfo
    {
        public string title;
        public string artist;
        public float bpm;
        public string source;       // "builtin" / "download" / "stream"
        public string localPath;    // 本地文件路径
        public string downloadUrl;  // 网络地址
        public AudioClip clip;
    }

    void Start()
    {
        _downloadDir = Path.Combine(Application.persistentDataPath, "NezhaMusic");
        Directory.CreateDirectory(_downloadDir);

        if (musicSource == null)
            musicSource = gameObject.AddComponent<AudioSource>();
        if (voiceSource == null)
            voiceSource = gameObject.AddComponent<AudioSource>();

        musicSource.loop = false;
        musicSource.playOnAwake = false;

        if (voiceGreeting == null)
            voiceGreeting = GetComponent<NezhaVoiceGreeting>();
        if (dancer == null)
            dancer = GetComponent<NezhaDancer>();

        // 初始化内置歌单
        InitBuiltInSongs();

        // 启动问候
        StartCoroutine(StartupGreeting());
    }

    void InitBuiltInSongs()
    {
        // 内置歌曲元数据（音频文件放 StreamingAssets/Music/）
        builtInSongs = new List<SongInfo>
        {
            new SongInfo { title = "哪吒", artist = "GAI周延", bpm = 140, source = "builtin",
                localPath = "Music/nezha_gai.mp3",
                downloadUrl = "https://music.163.com/song?id=1357780913" },
            new SongInfo { title = "就是哪吒", artist = "王一博", bpm = 128, source = "builtin",
                localPath = "Music/jiushi_nezha.mp3" },
            new SongInfo { title = "山河图", artist = "凤凰传奇", bpm = 110, source = "builtin",
                localPath = "Music/shanhetu.mp3",
                downloadUrl = "https://music.163.com/song?id=1861168802" },
            new SongInfo { title = "踏山河", artist = "七叔", bpm = 120, source = "builtin",
                localPath = "Music/tashanhe.mp3",
                downloadUrl = "https://music.163.com/song?id=1813868798" },
            new SongInfo { title = "骁", artist = "井胧/井迪", bpm = 100, source = "builtin",
                localPath = "Music/xiao.mp3" },
        };

        // 加载已有的内置音频
        foreach (var song in builtInSongs)
        {
            string path = Path.Combine(Application.streamingAssetsPath, song.localPath);
            if (File.Exists(path))
                StartCoroutine(LoadAudioClip(path, song));
        }
    }

    IEnumerator StartupGreeting()
    {
        yield return new WaitForSeconds(0.5f);
        if (voiceGreeting != null)
            voiceGreeting.Speak("你好，我是灵绘，可以唱歌跳舞的！", () =>
            {
                // 问候完自动播第一首
                if (builtInSongs.Count > 0)
                    PlaySong(0);
            });
    }

    /// <summary>播放指定索引的歌</summary>
    public void PlaySong(int index)
    {
        if (index < 0 || index >= builtInSongs.Count) return;

        _currentIndex = index;
        currentSong = builtInSongs[index];

        if (currentSong.clip != null)
        {
            PlayClip(currentSong.clip);
        }
        else if (!string.IsNullOrEmpty(currentSong.downloadUrl))
        {
            voiceGreeting?.Speak("正在下载 " + currentSong.title, () =>
                StartCoroutine(DownloadAndPlay(currentSong)));
        }
        else
        {
            voiceGreeting?.Speak("这首歌还没准备好呢，换一首吧");
        }
    }

    /// <summary>下一首</summary>
    public void NextSong()
    {
        if (builtInSongs.Count == 0) return;
        int next = (_currentIndex + 1) % builtInSongs.Count;
        PlaySong(next);
    }

    /// <summary>上一首</summary>
    public void PrevSong()
    {
        if (builtInSongs.Count == 0) return;
        int prev = (_currentIndex - 1 + builtInSongs.Count) % builtInSongs.Count;
        PlaySong(prev);
    }

    /// <summary>暂停/继续</summary>
    public void TogglePause()
    {
        if (isPlaying) { musicSource.Pause(); isPlaying = false; }
        else { musicSource.UnPause(); isPlaying = true; }
    }

    /// <summary>下载网络歌曲</summary>
    public void DownloadSong(string url, string title, float bpm, string artist = "未知")
    {
        var song = new SongInfo
        {
            title = title, artist = artist, bpm = bpm,
            source = "download", downloadUrl = url,
            localPath = Path.Combine(_downloadDir, SanitizeFileName(title) + ".mp3")
        };
        builtInSongs.Add(song);
        voiceGreeting?.Speak("开始下载 " + title, () =>
            StartCoroutine(DownloadAndPlay(song)));
    }

    IEnumerator DownloadAndPlay(SongInfo song)
    {
        string localPath = song.localPath;

        // 已下载则直接播放
        if (File.Exists(localPath))
        {
            yield return LoadAudioClip("file://" + localPath, song);
            if (song.clip != null) PlayClip(song.clip);
            yield break;
        }

        // 网络下载
        using (var req = UnityWebRequestMultimedia.GetAudioClip(song.downloadUrl, AudioType.MPEG))
        {
            req.timeout = 30;
            yield return req.SendWebRequest();

            if (req.result == UnityWebRequest.Result.Success)
            {
                song.clip = DownloadHandlerAudioClip.GetContent(req);
                PlayClip(song.clip);

                // 保存到本地
                SaveAudioToFile(song.downloadUrl, localPath);
            }
            else
            {
                voiceGreeting?.Speak("下载失败了，换一首吧");
                Debug.LogWarning($"下载失败: {req.error}");
            }
        }
    }

    void PlayClip(AudioClip clip)
    {
        musicSource.clip = clip;
        musicSource.Play();
        isPlaying = true;

        // BPM 同步舞蹈
        if (dancer != null && currentSong != null)
            dancer.SetBPM(currentSong.bpm);

        // 歌名播报
        if (currentSong != null)
            voiceGreeting?.Speak(currentSong.title + " — " + currentSong.artist);
    }

    IEnumerator LoadAudioClip(string path, SongInfo song)
    {
        using (var req = UnityWebRequestMultimedia.GetAudioClip(path, AudioType.MPEG))
        {
            yield return req.SendWebRequest();
            if (req.result == UnityWebRequest.Result.Success)
                song.clip = DownloadHandlerAudioClip.GetContent(req);
        }
    }

    void SaveAudioToFile(string url, string localPath)
    {
        StartCoroutine(SaveRoutine(url, localPath));
    }

    IEnumerator SaveRoutine(string url, string localPath)
    {
        using (var req = UnityWebRequest.Get(url))
        {
            yield return req.SendWebRequest();
            if (req.result == UnityWebRequest.Result.Success)
                File.WriteAllBytes(localPath, req.downloadHandler.data);
        }
    }

    string SanitizeFileName(string name)
    {
        foreach (char c in Path.GetInvalidFileNameChars())
            name = name.Replace(c, '_');
        return name;
    }

    void Update()
    {
        // 自动切歌
        if (isPlaying && !musicSource.isPlaying && musicSource.clip != null)
        {
            NextSong();
        }
    }

    void OnApplicationQuit()
    {
        if (isPlaying)
            musicSource.Stop();
    }
}
