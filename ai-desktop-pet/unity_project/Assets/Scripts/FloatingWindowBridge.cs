using UnityEngine;
using System.Collections;

/// <summary>
/// Android 悬浮窗桥接 —— 管理宠物在屏幕上的浮层显示。
/// 通过 AndroidJavaObject 调用系统 API 实现悬浮窗权限和窗口管理。
/// </summary>
public class FloatingWindowBridge : MonoBehaviour
{
    [Header("悬浮窗设置")]
    public int windowWidth = 400;
    public int windowHeight = 500;
    public int defaultX = 100;
    public int defaultY = 300;

    [Header("安全区域")]
    public int topSafeMargin = 80;   // 状态栏
    public int bottomSafeMargin = 120; // 导航栏

    private AndroidJavaObject _windowManager;
    private AndroidJavaObject _layoutParams;
    private bool _permissionGranted;

    void Start()
    {
#if UNITY_ANDROID && !UNITY_EDITOR
        StartCoroutine(RequestOverlayPermission());
#else
        Debug.Log("[FloatingWindow] 非 Android 环境，悬浮窗功能跳过");
        _permissionGranted = true;
#endif
    }

    IEnumerator RequestOverlayPermission()
    {
        using (var unityPlayer = new AndroidJavaClass("com.unity3d.player.UnityPlayer"))
        using (var activity = unityPlayer.GetStatic<AndroidJavaObject>("currentActivity"))
        {
            // 检查 SYSTEM_ALERT_WINDOW 权限
            using (var settings = new AndroidJavaClass("android.provider.Settings"))
            {
                bool canDraw = settings.CallStatic<bool>(
                    "canDrawOverlays", activity
                );

                if (!canDraw)
                {
                    Debug.Log("[FloatingWindow] 请求悬浮窗权限...");
                    // 引导用户去设置页面
                    using (var intent = new AndroidJavaObject("android.content.Intent",
                        "android.settings.action.MANAGE_OVERLAY_PERMISSION"))
                    using (var uri = new AndroidJavaClass("android.net.Uri"))
                    {
                        var packageUri = uri.CallStatic<AndroidJavaObject>(
                            "parse", $"package:{Application.identifier}"
                        );
                        intent.Call<AndroidJavaObject>("setData", packageUri);
                        activity.Call("startActivity", intent);
                    }

                    // 等待用户授权
                    float waited = 0f;
                    while (!canDraw && waited < 30f)
                    {
                        yield return new WaitForSeconds(0.5f);
                        waited += 0.5f;
                        canDraw = settings.CallStatic<bool>("canDrawOverlays", activity);
                    }
                }

                _permissionGranted = canDraw;
                Debug.Log($"[FloatingWindow] 悬浮窗权限: {(_permissionGranted ? "已授权" : "未授权")}");

                if (_permissionGranted)
                {
                    SetupFloatingWindow(activity);
                }
            }
        }
    }

    void SetupFloatingWindow(AndroidJavaObject activity)
    {
        // 获取 WindowManager
        using (var context = activity.Call<AndroidJavaObject>("getApplicationContext"))
        {
            _windowManager = context.Call<AndroidJavaObject>(
                "getSystemService", "window"
            );

            // 创建 LayoutParams（TYPE_APPLICATION_OVERLAY）
            int typeApplicationOverlay = 2038; // TYPE_APPLICATION_OVERLAY (API 26+)
            int flagNotFocusable = 0x00000008;
            int flagNotTouchModal = 0x00000020;
            int flagLayoutNoLimits = 0x00000200;
            int gravityTopLeft = 51;

            _layoutParams = new AndroidJavaObject(
                "android.view.WindowManager$LayoutParams",
                windowWidth, windowHeight,
                defaultX, defaultY,
                typeApplicationOverlay,
                flagNotFocusable | flagNotTouchModal | flagLayoutNoLimits,
                -2 // PixelFormat.TRANSLUCENT
            );

            _layoutParams.Set("gravity", gravityTopLeft);
        }

        Debug.Log("[FloatingWindow] 悬浮窗参数已配置");
    }

    /// <summary>更新悬浮窗位置（由 PetCore 拖动时调用）</summary>
    public void UpdatePosition(int x, int y)
    {
        if (_layoutParams == null || _windowManager == null) return;

        // 限制在安全区域内
        x = Mathf.Max(0, x);
        y = Mathf.Max(topSafeMargin, y);
        y = Mathf.Min(Screen.height - bottomSafeMargin - windowHeight, y);

        _layoutParams.Set("x", x);
        _layoutParams.Set("y", y);

        try
        {
            // 更新布局参数（需要 View 引用，这里是通过 Unity 的 SurfaceView 实现）
            // 实际项目中需要通过 UnityPlayer 的 addView/updateViewLayout 操作
            _windowManager.Call("updateViewLayout", _layoutParams, _layoutParams);
        }
        catch (System.Exception e)
        {
            Debug.LogWarning($"[FloatingWindow] 更新位置失败: {e.Message}");
        }
    }

    /// <summary>最小化宠物到屏幕边缘</summary>
    public void MinimizeToEdge()
    {
        int edgeX = Screen.width - 80; // 缩到右边
        int edgeY = defaultY;
        UpdatePosition(edgeX, edgeY);
    }

    void OnApplicationQuit()
    {
        if (_windowManager != null && _layoutParams != null)
        {
            try
            {
                _windowManager.Call("removeView", _layoutParams);
            }
            catch { }
        }
    }
}
