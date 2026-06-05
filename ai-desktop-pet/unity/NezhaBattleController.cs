using UnityEngine;
using System.Collections;

/// <summary>
/// 哪吒战鬪总控 — 统一管理风火轮/混天绫/瞳孔燃烧三件套
/// 由 PetEmotionSystem 调用 SetFiredUp()
/// </summary>
public class NezhaBattleController : MonoBehaviour
{
    [Header("三件套组件")]
    public NezhaFireWheels fireWheels;
    public NezhaSashFlutter sashFlutter;
    public Renderer[] eyeRenderers; // 使用 Nezha/EyeFiredUp Shader 的渲染器

    [Header("变身参数")]
    public float transformDuration = 0.5f;  // 变身过渡时长
    public AnimationCurve transformCurve = AnimationCurve.EaseInOut(0, 0, 1, 1);

    [Header("屏幕震动")]
    public float shakeIntensity = 0.3f;
    public float shakeDuration = 0.4f;

    [Header("音效触发")]
    public AudioSource audioSource;
    public AudioClip firedUpClip;
    public AudioClip flameLoopClip;

    private bool _isFiredUp;
    private float _burnLerp;
    private Coroutine _transformRoutine;

    // MaterialPropertyBlock 缓存
    private MaterialPropertyBlock _propBlock;
    private static readonly int FiredUpID = Shader.PropertyToID("_FiredUp");
    private static readonly int BurnGlowID = Shader.PropertyToID("_BurnGlow");

    void Start()
    {
        _propBlock = new MaterialPropertyBlock();

        // 自动查找
        if (fireWheels == null) fireWheels = GetComponentInChildren<NezhaFireWheels>();
        if (sashFlutter == null) sashFlutter = GetComponentInChildren<NezhaSashFlutter>();
        if (eyeRenderers == null || eyeRenderers.Length == 0)
        {
            var all = GetComponentsInChildren<Renderer>();
            var list = new System.Collections.Generic.List<Renderer>();
            foreach (var r in all)
                foreach (var m in r.sharedMaterials)
                    if (m != null && m.name.Contains("Eye"))
                        list.Add(r);
            eyeRenderers = list.ToArray();
        }
    }

    /// <summary>切换战鬪形态 — 由 PetEmotionSystem 调用</summary>
    public void SetFiredUp(bool active)
    {
        if (_isFiredUp == active) return;
        _isFiredUp = active;

        if (_transformRoutine != null)
            StopCoroutine(_transformRoutine);
        _transformRoutine = StartCoroutine(TransformRoutine(active));
    }

    IEnumerator TransformRoutine(bool entering)
    {
        float t = 0f;
        float start = entering ? 0f : 1f;
        float end = entering ? 1f : 0f;

        // 入场 → 屏幕震动
        if (entering && Mathf.Abs(shakeIntensity) > 0.001f)
        {
            var cam = Camera.main;
            if (cam != null)
            {
                var shaker = cam.GetComponent<NezhaCameraShake>();
                if (shaker == null) shaker = cam.gameObject.AddComponent<NezhaCameraShake>();
                shaker.Shake(shakeIntensity, shakeDuration);
            }
        }

        // 入场 → 音效
        if (entering && audioSource != null && firedUpClip != null)
            audioSource.PlayOneShot(firedUpClip);

        // 粒子爆发立即触发
        if (fireWheels != null)
            fireWheels.SetFiredUp(entering);

        // 飘带立即切换
        if (sashFlutter != null)
            sashFlutter.SetFiredUp(entering);

        // 瞳孔渐变过渡
        while (t < transformDuration)
        {
            t += Time.deltaTime;
            float v = Mathf.Lerp(start, end, transformCurve.Evaluate(t / transformDuration));
            SetEyeBurn(v);
            yield return null;
        }
        SetEyeBurn(end);

        // 入场 → 循环火焰音效
        if (entering && audioSource != null && flameLoopClip != null)
        {
            audioSource.clip = flameLoopClip;
            audioSource.loop = true;
            audioSource.Play();
        }
        else if (!entering && audioSource != null)
        {
            audioSource.loop = false;
            audioSource.Stop();
        }

        _transformRoutine = null;
    }

    void SetEyeBurn(float value)
    {
        foreach (var r in eyeRenderers)
        {
            if (r == null) continue;
            r.GetPropertyBlock(_propBlock);
            _propBlock.SetFloat(FiredUpID, value);
            _propBlock.SetFloat(BurnGlowID, value * 2f);
            r.SetPropertyBlock(_propBlock);
        }
    }

    /// <summary>立即触发一个小爆发（不进入持续 fired_up）</summary>
    public void BurstFlame()
    {
        if (fireWheels != null)
        {
            fireWheels.SetFiredUp(true);
            StartCoroutine(ResetAfterDelay(0.3f));
        }
    }

    IEnumerator ResetAfterDelay(float delay)
    {
        yield return new WaitForSeconds(delay);
        if (!_isFiredUp && fireWheels != null)
            fireWheels.SetFiredUp(false);
    }
}

/// <summary>简易相机震动</summary>
public class NezhaCameraShake : MonoBehaviour
{
    public void Shake(float intensity, float duration)
    {
        StartCoroutine(ShakeRoutine(intensity, duration));
    }

    IEnumerator ShakeRoutine(float intensity, float duration)
    {
        Vector3 origin = transform.localPosition;
        float t = 0;
        while (t < duration)
        {
            t += Time.deltaTime;
            float decay = 1 - t / duration;
            float x = (Mathf.PerlinNoise(t * 30f, 0) - 0.5f) * intensity * decay;
            float y = (Mathf.PerlinNoise(0, t * 30f) - 0.5f) * intensity * decay;
            transform.localPosition = origin + new Vector3(x, y, 0);
            yield return null;
        }
        transform.localPosition = origin;
    }
}
