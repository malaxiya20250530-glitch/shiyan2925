using UnityEngine;
using UnityEngine.Networking;
using System.Collections;
using System.Collections.Generic;
using System.IO;
using System.Text;

/// <summary>
/// 灵辉歌曲下载器 — 从免费音源下载歌曲
/// 支持：本地缓存 / 直链下载 / 免费 API 搜索
/// </summary>
public class NezhaSongDownloader : MonoBehaviour
{
    [Header("下载目录")]
    public string downloadDir;

    [Header("免费音源 API")]
    public string searchApiUrl = "";  // 自定义搜索 API
    public bool useFreeSources = true;

    [Header("状态")]
    public List<DownloadTask> downloadQueue = new List<DownloadTask>();
    public int maxConcurrent = 2;

    [Header("联动")]
    public NezhaMusicPlayer musicPlayer;
    public NezhaVoiceGreeting voice;

    private int _activeDownloads;

    [System.Serializable]
    public class DownloadTask
    {
        public string title;
        public string artist;
        public string url;
        public float bpm;
        public DownloadStatus status;
        public float progress;
        public string localPath;
    }

    public enum DownloadStatus { Queued, Downloading, Done, Failed }

    void Start()
    {
        if (string.IsNullOrEmpty(downloadDir))
            downloadDir = Path.Combine(Application.persistentDataPath, "NezhaMusic");
        Directory.CreateDirectory(downloadDir);

        if (musicPlayer == null) musicPlayer = GetComponent<NezhaMusicPlayer>();
        if (voice == null) voice = GetComponent<NezhaVoiceGreeting>();
    }

    /// <summary>搜索并下载歌曲</summary>
    public void SearchAndDownload(string keyword)
    {
        if (voice != null)
            voice.Speak("正在搜索 " + keyword, () =>
                StartCoroutine(SearchOnline(keyword)));
        else
            StartCoroutine(SearchOnline(keyword));
    }

    /// <summary>直接下载（已知 URL）</summary>
    public void DirectDownload(string url, string title, string artist = "未知", float bpm = 120)
    {
        var task = new DownloadTask
        {
            title = title, artist = artist, url = url, bpm = bpm,
            status = DownloadStatus.Queued,
            localPath = Path.Combine(downloadDir, Sanitize(title) + ".mp3")
        };

        // 已缓存
        if (File.Exists(task.localPath))
        {
            task.status = DownloadStatus.Done;
            AddToMusicPlayer(task);
            return;
        }

        downloadQueue.Add(task);
        ProcessQueue();
    }

    IEnumerator SearchOnline(string keyword)
    {
        if (!useFreeSources || string.IsNullOrEmpty(searchApiUrl))
        {
            // 使用内置免费源列表
            var results = GetBuiltInFreeSongs(keyword);
            foreach (var song in results)
                DirectDownload(song.url, song.title, song.artist, song.bpm);
            yield break;
        }

        string url = searchApiUrl.Replace("{KEYWORD}", UnityWebRequest.EscapeURL(keyword));
        using (var req = UnityWebRequest.Get(url))
        {
            req.timeout = 10;
            yield return req.SendWebRequest();

            if (req.result == UnityWebRequest.Result.Success)
            {
                // 解析搜索结果（JSON 格式）
                var results = ParseSearchResults(req.downloadHandler.text);
                foreach (var song in results)
                    DirectDownload(song.url, song.title, song.artist, song.bpm);

                if (voice != null)
                    voice.Speak($"找到 {results.Count} 首歌");
            }
            else
            {
                if (voice != null)
                    voice.Speak("搜索失败，试试内置歌单吧");
            }
        }
    }

    /// <summary>内置免费歌曲源（替换为公共领域/CC 授权音乐）</summary>
    List<(string url, string title, string artist, float bpm)> GetBuiltInFreeSongs(string keyword)
    {
        var all = new List<(string url, string title, string artist, float bpm)>
        {
            // 公共领域 / CC0 音乐（用互联网档案馆等免费源）
            ("https://archive.org/download/nezha-theme/nezha.mp3", "哪吒主题", "传统民乐", 130),
            ("https://freepd.com/music/Chinese%20Dance.mp3", "中国舞曲", "FreePD", 110),
            ("https://freepd.com/music/Epic%20Trailer.mp3", "史诗战歌", "FreePD", 140),
        };

        if (string.IsNullOrEmpty(keyword)) return all;

        return all.FindAll(s =>
            s.title.Contains(keyword) || s.artist.Contains(keyword));
    }

    List<(string url, string title, string artist, float bpm)> ParseSearchResults(string json)
    {
        var results = new List<(string, string, string, float)>();
        try
        {
            var data = JsonUtility.FromJson<SearchResponse>(json);
            if (data?.songs != null)
            {
                foreach (var s in data.songs)
                    results.Add((s.url, s.title, s.artist, s.bpm));
            }
        }
        catch { /* 解析失败，返回空 */ }
        return results;
    }

    [System.Serializable]
    class SearchResponse { public List<SongData> songs; }
    [System.Serializable]
    class SongData { public string url, title, artist; public float bpm; }

    void ProcessQueue()
    {
        while (_activeDownloads < maxConcurrent && downloadQueue.Exists(t => t.status == DownloadStatus.Queued))
        {
            var task = downloadQueue.Find(t => t.status == DownloadStatus.Queued);
            if (task == null) break;

            task.status = DownloadStatus.Downloading;
            _activeDownloads++;
            StartCoroutine(DownloadRoutine(task));
        }
    }

    IEnumerator DownloadRoutine(DownloadTask task)
    {
        // 先用 HEAD 检查
        using (var req = UnityWebRequest.Get(task.url))
        {
            req.timeout = 30;
            req.downloadHandler = new DownloadHandlerFile(task.localPath);

            var op = req.SendWebRequest();
            while (!op.isDone)
            {
                task.progress = req.downloadProgress;
                yield return null;
            }

            _activeDownloads--;

            if (req.result == UnityWebRequest.Result.Success)
            {
                task.status = DownloadStatus.Done;
                task.progress = 1f;
                AddToMusicPlayer(task);

                if (voice != null)
                    voice.Speak(task.title + " 下载完成！");
            }
            else
            {
                task.status = DownloadStatus.Failed;
                Debug.LogWarning($"下载失败 {task.title}: {req.error}");
            }

            ProcessQueue();
        }
    }

    void AddToMusicPlayer(DownloadTask task)
    {
        if (musicPlayer == null) return;

        musicPlayer.DownloadSong(task.url, task.title, task.bpm, task.artist);
    }

    /// <summary>获取下载进度</summary>
    public float GetOverallProgress()
    {
        if (downloadQueue.Count == 0) return 0;
        float total = 0;
        foreach (var t in downloadQueue)
            total += t.progress;
        return total / downloadQueue.Count;
    }

    string Sanitize(string name)
    {
        foreach (char c in Path.GetInvalidFileNameChars())
            name = name.Replace(c, '_');
        return name;
    }
}
