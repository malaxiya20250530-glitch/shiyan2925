using System;
using System.Collections;
using System.Net.WebSockets;
using System.Text;
using System.Threading;
using System.Threading.Tasks;
using UnityEngine;

/// <summary>
/// AI 响应数据结构，对应 Python 后端的 pet_response。
/// </summary>
[System.Serializable]
public class PetResponse
{
    public string type;
    public string text;
    public string emotion;
    public string animation;
    public string triggered_emotion;

    // emotion_values 在 Unity 侧用 JSON 字符串处理
    public string emotion_values_json;

    // 自动化相关
    public string pending_action_json;
    public string action_result_json;
}

/// <summary>
/// WebSocket 客户端，连接 Python 后端 AI 服务。
/// 挂载到 PetCore 所在的 GameObject。
/// </summary>
public class AIConnector : MonoBehaviour
{
    [Header("连接设置")]
    public string serverUrl = "ws://127.0.0.1:9527";
    public float reconnectInterval = 3f;
    public int maxReconnectAttempts = 10;

    // 事件
    public event Action<PetResponse> OnResponseReceived;
    public event Action OnConnected;
    public event Action<string> OnError;

    // 内部状态
    private ClientWebSocket _ws;
    private CancellationTokenSource _cts;
    private bool _shouldReconnect = true;
    private int _reconnectCount;
    private readonly byte[] _buffer = new byte[8192];

    public bool IsConnected => _ws?.State == WebSocketState.Open;

    void Start()
    {
        _ = ConnectAsync();
    }

    void OnDestroy()
    {
        _shouldReconnect = false;
        _cts?.Cancel();
        _ws?.Dispose();
    }

    void OnApplicationPause(bool pauseStatus)
    {
        if (!pauseStatus)
        {
            _shouldReconnect = true;
            _reconnectCount = 0;
            _ = ConnectAsync();
        }
        else
        {
            _shouldReconnect = false;
            _cts?.Cancel();
        }
    }

    // ─── 连接管理 ───

    async Task ConnectAsync()
    {
        while (_shouldReconnect && _reconnectCount < maxReconnectAttempts)
        {
            try
            {
                _cts = new CancellationTokenSource();
                _ws = new ClientWebSocket();

                Debug.Log($"[AIConnector] 正在连接 {serverUrl}...");
                await _ws.ConnectAsync(new Uri(serverUrl), _cts.Token);

                Debug.Log("[AIConnector] ✓ 已连接到 AI 后端");
                _reconnectCount = 0;
                OnConnected?.Invoke();

                // 开始接收消息
                await ReceiveLoop();
            }
            catch (Exception e)
            {
                Debug.LogWarning($"[AIConnector] 连接失败: {e.Message}");
                OnError?.Invoke(e.Message);

                _reconnectCount++;
                if (_shouldReconnect && _reconnectCount < maxReconnectAttempts)
                {
                    Debug.Log($"[AIConnector] {reconnectInterval}s 后重试 ({_reconnectCount}/{maxReconnectAttempts})...");
                    await Task.Delay((int)(reconnectInterval * 1000));
                }
            }
        }

        if (_reconnectCount >= maxReconnectAttempts)
        {
            Debug.LogError("[AIConnector] 达到最大重连次数，停止重连。");
        }
    }

    // ─── 消息收发 ───

    async Task ReceiveLoop()
    {
        var sb = new StringBuilder();

        while (_ws?.State == WebSocketState.Open && !_cts.Token.IsCancellationRequested)
        {
            try
            {
                var result = await _ws.ReceiveAsync(
                    new ArraySegment<byte>(_buffer), _cts.Token
                );

                if (result.MessageType == WebSocketMessageType.Close)
                {
                    Debug.Log("[AIConnector] 服务器关闭连接");
                    await _ws.CloseAsync(WebSocketCloseStatus.NormalClosure, "", CancellationToken.None);
                    break;
                }

                sb.Append(Encoding.UTF8.GetString(_buffer, 0, result.Count));

                if (result.EndOfMessage)
                {
                    string json = sb.ToString();
                    sb.Clear();

                    // 在主线程处理
                    UnityMainThreadDispatcher.Enqueue(() => ProcessMessage(json));
                }
            }
            catch (OperationCanceledException)
            {
                break;
            }
            catch (WebSocketException e)
            {
                Debug.LogWarning($"[AIConnector] 接收异常: {e.Message}");
                break;
            }
        }

        // 连接断开，尝试重连
        if (_shouldReconnect)
        {
            _ = ConnectAsync();
        }
    }

    public async void SendMessage(string jsonMessage)
    {
        if (_ws?.State != WebSocketState.Open)
        {
            Debug.LogWarning("[AIConnector] 未连接，无法发送消息");
            return;
        }

        try
        {
            byte[] data = Encoding.UTF8.GetBytes(jsonMessage);
            await _ws.SendAsync(
                new ArraySegment<byte>(data),
                WebSocketMessageType.Text,
                true,
                _cts.Token
            );
        }
        catch (Exception e)
        {
            Debug.LogError($"[AIConnector] 发送失败: {e.Message}");
        }
    }

    /// <summary>发送用户输入到 AI 后端</summary>
    public void SendUserInput(string text)
    {
        string json = $"{{\"type\":\"user_input\",\"content\":\"{EscapeJson(text)}\"}}";
        SendMessage(json);
    }

    // ─── 消息处理 ───

    void ProcessMessage(string json)
    {
        try
        {
            var response = JsonUtility.FromJson<PetResponse>(json);

            if (response.type == "pet_response")
            {
                OnResponseReceived?.Invoke(response);
            }
            else if (response.type == "pong")
            {
                Debug.Log("[AIConnector] 心跳响应");
            }
        }
        catch (Exception e)
        {
            Debug.LogError($"[AIConnector] 消息解析失败: {e.Message}\n原始: {json}");
        }
    }

    string EscapeJson(string text)
    {
        return text.Replace("\\", "\\\\")
                   .Replace("\"", "\\\"")
                   .Replace("\n", "\\n")
                   .Replace("\r", "\\r");
    }
}


/// <summary>
/// Unity 主线程调度器 —— 将回调投递到主线程执行。
/// 放置于场景中作为单例。
/// </summary>
public class UnityMainThreadDispatcher : MonoBehaviour
{
    private static readonly System.Collections.Generic.Queue<Action> _queue
        = new System.Collections.Generic.Queue<Action>();
    private static UnityMainThreadDispatcher _instance;

    void Awake()
    {
        if (_instance == null)
        {
            _instance = this;
            DontDestroyOnLoad(gameObject);
        }
    }

    void Update()
    {
        lock (_queue)
        {
            while (_queue.Count > 0)
            {
                _queue.Dequeue()?.Invoke();
            }
        }
    }

    public static void Enqueue(Action action)
    {
        lock (_queue)
        {
            _queue.Enqueue(action);
        }
    }
}
