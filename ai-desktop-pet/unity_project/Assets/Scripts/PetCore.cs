using UnityEngine;
using System.Collections;

/// <summary>
/// 宠物核心控制器 —— 管理宠物生命周期、动画触发、交互响应。
/// 挂载到宠物根 GameObject 上。
/// </summary>
public class PetCore : MonoBehaviour
{
    [Header("组件引用")]
    public Animator animator;
    public AIConnector aiConnector;
    public PetEmotionSystem emotionSystem;
    public SpeechBubble speechBubble;
    public FloatingWindowBridge floatingWindow;

    [Header("交互设置")]
    public float doubleClickTime = 0.4f;
    public float dragThreshold = 20f;
    public float idleAnimationInterval = 15f;

    // 内部状态
    private float _lastClickTime;
    private bool _isDragging;
    private Vector3 _dragOffset;
    private Camera _mainCamera;
    private float _idleTimer;
    private bool _isSpeaking;

    void Start()
    {
        _mainCamera = Camera.main;
        if (animator == null) animator = GetComponent<Animator>();
        if (emotionSystem == null) emotionSystem = GetComponent<PetEmotionSystem>();
        if (aiConnector == null) aiConnector = GetComponent<AIConnector>();
        if (speechBubble == null) speechBubble = GetComponentInChildren<SpeechBubble>();
        if (floatingWindow == null) floatingWindow = GetComponent<FloatingWindowBridge>();

        // 订阅 AI 回复事件
        if (aiConnector != null)
        {
            aiConnector.OnResponseReceived += HandleAIResponse;
        }

        // 打招呼
        StartCoroutine(GreetOnStart());
    }

    void Update()
    {
        HandleIdleAnimations();

        // 触摸交互
        if (Input.touchCount > 0)
        {
            Touch touch = Input.GetTouch(0);
            switch (touch.phase)
            {
                case TouchPhase.Began:
                    OnTouchBegan(touch);
                    break;
                case TouchPhase.Moved:
                    OnTouchMoved(touch);
                    break;
                case TouchPhase.Ended:
                    OnTouchEnded(touch);
                    break;
            }
        }

        // 鼠标交互（编辑器测试用）
        if (Input.GetMouseButtonDown(0))
        {
            OnMouseDown();
        }
    }

    // ─── 触摸交互 ───

    void OnTouchBegan(Touch touch)
    {
        Ray ray = _mainCamera.ScreenPointToRay(touch.position);
        if (Physics.Raycast(ray, out RaycastHit hit) && hit.collider.gameObject == gameObject)
        {
            _dragOffset = transform.position - GetWorldPoint(touch.position);
            _isDragging = false;
        }
    }

    void OnTouchMoved(Touch touch)
    {
        if (Vector2.Distance(touch.deltaPosition, Vector2.zero) > dragThreshold)
        {
            _isDragging = true;
            Vector3 targetPos = GetWorldPoint(touch.position) + _dragOffset;
            transform.position = targetPos;
        }
    }

    void OnTouchEnded(Touch touch)
    {
        if (!_isDragging)
        {
            float timeSinceLast = Time.time - _lastClickTime;
            _lastClickTime = Time.time;

            if (timeSinceLast < doubleClickTime)
            {
                OnDoubleClick();
            }
            else
            {
                OnSingleClick();
            }
        }
        _isDragging = false;
    }

    void OnMouseDown()
    {
        float timeSinceLast = Time.time - _lastClickTime;
        _lastClickTime = Time.time;
        if (timeSinceLast < doubleClickTime)
            OnDoubleClick();
        else
            OnSingleClick();
    }

    // ─── 交互响应 ───

    /// <summary>单击：播放反馈动画 + 随机短语</summary>
    void OnSingleClick()
    {
        emotionSystem.TriggerEmotion("happy", 0.2f);
        PlayAnimation("bounce");

        if (aiConnector != null && aiConnector.IsConnected)
        {
            aiConnector.SendMessage("get_status");
        }
    }

    /// <summary>双击：开启对话模式</summary>
    void OnDoubleClick()
    {
        emotionSystem.TriggerEmotion("excited", 0.3f);
        PlayAnimation("spin");
        ShowSpeechBubble("有什么想和我说的吗？✨");
    }

    // ─── AI 回调 ───

    void HandleAIResponse(PetResponse response)
    {
        // 更新情绪
        if (!string.IsNullOrEmpty(response.emotion))
        {
            emotionSystem.TriggerEmotion(response.emotion, 0.3f);
        }

        // 播放动画
        if (!string.IsNullOrEmpty(response.animation))
        {
            PlayAnimation(response.animation);
        }

        // 显示对话气泡
        if (!string.IsNullOrEmpty(response.text))
        {
            ShowSpeechBubble(response.text);
        }
    }

    void HandleIdleAnimations()
    {
        if (_isSpeaking) return;
        _idleTimer += Time.deltaTime;
        if (_idleTimer > idleAnimationInterval)
        {
            _idleTimer = 0f;
            string[] idles = { "idle", "yawn", "stretch", "look_around" };
            string randomIdle = idles[Random.Range(0, idles.Length)];
            PlayAnimation(randomIdle);
        }
    }

    // ─── 辅助方法 ───

    void PlayAnimation(string animName)
    {
        if (animator != null)
        {
            animator.SetTrigger(animName);
        }
    }

    void ShowSpeechBubble(string text)
    {
        if (speechBubble != null)
        {
            _isSpeaking = true;
            speechBubble.Show(text, () => { _isSpeaking = false; });
        }
    }

    IEnumerator GreetOnStart()
    {
        yield return new WaitForSeconds(0.5f);
        PlayAnimation("wave");
        yield return new WaitForSeconds(0.3f);
        ShowSpeechBubble("嗨！我来啦~ 🐾");
    }

    Vector3 GetWorldPoint(Vector2 screenPoint)
    {
        Vector3 worldPos = _mainCamera.ScreenToWorldPoint(
            new Vector3(screenPoint.x, screenPoint.y, 10f)
        );
        worldPos.z = 0;
        return worldPos;
    }
}
