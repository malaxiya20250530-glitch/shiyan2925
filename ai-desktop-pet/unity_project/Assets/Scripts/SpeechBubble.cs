using UnityEngine;
using UnityEngine.UI;
using System.Collections;
using System;

/// <summary>
/// 对话气泡组件 —— 显示宠物说的话，带淡入淡出和自动消失。
/// 挂载到 Canvas 下的气泡 GameObject。
/// </summary>
public class SpeechBubble : MonoBehaviour
{
    [Header("UI 引用")]
    public Text bubbleText;
    public Image bubbleBackground;
    public CanvasGroup canvasGroup;

    [Header("动画设置")]
    public float fadeInDuration = 0.3f;
    public float displayDuration = 3f;
    public float fadeOutDuration = 0.5f;
    public float typewriterSpeed = 0.05f; // 打字机效果，每字间隔秒

    private Coroutine _currentBubble;
    private Action _onComplete;

    void Awake()
    {
        if (canvasGroup == null) canvasGroup = GetComponent<CanvasGroup>();
        if (canvasGroup != null) canvasGroup.alpha = 0f;
    }

    /// <summary>显示对话气泡，完成后回调</summary>
    public void Show(string text, Action onComplete = null, float customDuration = -1f)
    {
        if (_currentBubble != null)
        {
            StopCoroutine(_currentBubble);
        }

        float duration = customDuration > 0 ? customDuration : displayDuration;
        _currentBubble = StartCoroutine(BubbleRoutine(text, duration, onComplete));
    }

    /// <summary>立即隐藏气泡</summary>
    public void Hide()
    {
        if (_currentBubble != null)
        {
            StopCoroutine(_currentBubble);
            _currentBubble = null;
        }
        StartCoroutine(FadeOut(fadeOutDuration * 0.3f));
    }

    // ─── 内部动画协程 ───

    IEnumerator BubbleRoutine(string text, float displayTime, Action onComplete)
    {
        // 淡入
        yield return StartCoroutine(FadeIn(fadeInDuration));

        // 打字机效果
        if (bubbleText != null)
        {
            yield return StartCoroutine(TypewriterEffect(text));
        }

        // 显示持续
        yield return new WaitForSeconds(displayTime);

        // 淡出
        yield return StartCoroutine(FadeOut(fadeOutDuration));

        onComplete?.Invoke();
        _currentBubble = null;
    }

    IEnumerator FadeIn(float duration)
    {
        if (canvasGroup == null) yield break;

        float elapsed = 0f;
        while (elapsed < duration)
        {
            elapsed += Time.deltaTime;
            canvasGroup.alpha = Mathf.Lerp(0f, 1f, elapsed / duration);
            yield return null;
        }
        canvasGroup.alpha = 1f;
    }

    IEnumerator FadeOut(float duration)
    {
        if (canvasGroup == null) yield break;

        float elapsed = 0f;
        float startAlpha = canvasGroup.alpha;
        while (elapsed < duration)
        {
            elapsed += Time.deltaTime;
            canvasGroup.alpha = Mathf.Lerp(startAlpha, 0f, elapsed / duration);
            yield return null;
        }
        canvasGroup.alpha = 0f;
        if (bubbleText != null) bubbleText.text = "";
    }

    IEnumerator TypewriterEffect(string fullText)
    {
        bubbleText.text = "";
        foreach (char c in fullText)
        {
            bubbleText.text += c;
            yield return new WaitForSeconds(typewriterSpeed);
        }
    }
}
